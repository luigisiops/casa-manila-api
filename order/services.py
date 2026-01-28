"""
Business logic and service functions for order management.
"""

from decimal import Decimal
from django.db import transaction
from order.models import Order, ItemOrder
from food_item.models import FoodItem


def create_item_order(
        order: Order, item: 'FoodItem', quantity: int, unit_price: Decimal = None
) -> ItemOrder:
    """
    Create a new ItemOrder with proper price locking and subtotal updates.
    
    This function encapsulates all the business logic for creating an ItemOrder:
    - Validates that the order is not COMPLETED
    - Locks the price at creation time from FoodItem if not provided
    - Calculates line_total automatically
    - Updates the order subtotal atomically
    
    Args:
        order: The order to add the item to.
        item: The FoodItem being ordered.
        quantity: The quantity being ordered (must be >= 1).
        unit_price: Optional price override. If None, uses item.price.
    
    Returns:
        ItemOrder: The created item order.
    
    Raises:
        ValueError: If the order status is COMPLETED.
    """
    with transaction.atomic():
        # Lock the order to prevent concurrent modifications
        locked_order = Order.objects.select_for_update().get(pk=order.pk)

        if locked_order.status == 'COMPLETED':
            raise ValueError("Cannot add items to a completed order")

        # Capture current price if not provided
        if unit_price is None:
            unit_price = item.price

        # Calculate line total
        line_total = quantity * unit_price

        # Create the ItemOrder without triggering complex save logic
        item_order = ItemOrder.objects.create(
            order=locked_order,
            item=item,
            quantity=quantity,
            unit_price=unit_price,
            line_total=line_total
        )

        # Recalculate order subtotal
        locked_order.subtotal = sum(io.line_total for io in locked_order.item_orders.all())
        locked_order.save(update_fields=['subtotal'])

        # Update the original order instance
        order.subtotal = locked_order.subtotal

        return item_order


def update_item_order(item_order: ItemOrder, quantity: int = None) -> ItemOrder:
    """
    Update an existing ItemOrder with automatic line_total and subtotal recalculation.
    
    Args:
        item_order: The ItemOrder to update.
        quantity: New quantity. If None, keeps existing quantity.
    
    Returns:
        ItemOrder: The updated item order.
    
    Raises:
        ValueError: If the order status is COMPLETED.
    """
    with transaction.atomic():
        # Lock the order to prevent concurrent modifications
        locked_order = Order.objects.select_for_update().get(pk=item_order.order.pk)

        if locked_order.status == 'COMPLETED':
            raise ValueError("Cannot modify ItemOrder for a completed order")

        # Update quantity if provided
        if quantity is not None:
            item_order.quantity = quantity

        # Recalculate line_total
        item_order.line_total = item_order.quantity * item_order.unit_price
        item_order.save(update_fields=['quantity', 'line_total', 'updated_at'])

        # Recalculate order subtotal
        locked_order.subtotal = sum(io.line_total for io in locked_order.item_orders.all())
        locked_order.save(update_fields=['subtotal'])

        return item_order


def delete_item_order(item_order: ItemOrder) -> None:
    """
    Delete an ItemOrder and update the order subtotal atomically.
    
    Args:
        item_order: The ItemOrder to delete.
    
    Raises:
        ValueError: If the order status is COMPLETED.
    """
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=item_order.order.pk)

        if order.status == 'COMPLETED':
            raise ValueError("Cannot delete ItemOrder for a completed order")

        item_order.delete()

        # Recalculate order subtotal after deletion
        order.subtotal = sum(io.line_total for io in order.item_orders.all())
        order.save(update_fields=['subtotal'])


def create_order_with_items(data: dict) -> Order:
    """
    Create an order with associated item orders in a single atomic transaction.
    
    Args:
        data: Dictionary containing order fields and optional 'items' list.
              items list format: [{'item': <FoodItem id>, 'quantity': <int>}, ...]
    
    Returns:
        Order: The created order with all item orders and calculated subtotal.
    
    Raises:
        FoodItem.DoesNotExist: If any item ID in the items list doesn't exist.
        ValueError: If quantity is invalid or order data is incomplete.
    """
    items_data = data.pop('items', [])

    with transaction.atomic():
        # Create the order with provided data
        order = Order.objects.create(**data)

        # Create all item orders using the service function
        for item_data in items_data:
            item_id = item_data['item']
            quantity = item_data['quantity']

            # Fetch the FoodItem to get current price
            food_item = FoodItem.objects.get(id=item_id)

            # Use create_item_order service (without transaction since we're already in one)
            # Manually create to avoid nested transaction issues
            unit_price = food_item.price
            line_total = quantity * unit_price

            ItemOrder.objects.create(
                order=order,
                item=food_item,
                quantity=quantity,
                unit_price=unit_price,
                line_total=line_total
            )

        # Calculate subtotal from all item orders
        order.subtotal = sum(io.line_total for io in order.item_orders.all())
        order.save(update_fields=['subtotal'])

    return order


def recalculate_order_subtotal(order: Order) -> None:
    """
    Recalculate and persist the order's subtotal based on all active item orders.
    
    This function acquires a row-level lock on the order to ensure consistency
    in concurrent scenarios.
    
    Args:
        order: The order instance to recalculate subtotal for.
    
    Raises:
        ValueError: If the order status is COMPLETED.
    """
    with transaction.atomic():
        # Lock the order to prevent concurrent modifications
        locked_order = Order.objects.select_for_update().get(pk=order.pk)

        # Prevent recalculation for completed orders
        if locked_order.status == 'COMPLETED':
            raise ValueError("Cannot modify a completed order")

        # Sum up line totals from all active item orders
        subtotal = sum(
            item.line_total for item in locked_order.item_orders.filter(is_active=True)
        )

        locked_order.subtotal = subtotal
        locked_order.save(update_fields=['subtotal'])

        # Update the original order instance to reflect changes
        order.subtotal = subtotal


def add_or_update_order_items(order: Order, items_data: list[dict]) -> None:
    """
    Add or update item orders for an existing order, maintaining transactional integrity.
    
    This function:
    - Creates new item orders with current food item prices
    - Updates quantities on existing item orders
    - Removes items not in the provided list
    - Recalculates the order subtotal after all changes
    
    Args:
        order: The order to update items for.
        items_data: List of item data dicts with format:
                   [{'item': <FoodItem id>, 'quantity': <int>}, ...]
    
    Raises:
        ValueError: If the order status is COMPLETED.
        FoodItem.DoesNotExist: If any item ID doesn't exist.
    """
    with transaction.atomic():
        # Lock the order to prevent concurrent modifications
        locked_order = Order.objects.select_for_update().get(pk=order.pk)

        # Prevent modifications to completed orders
        if locked_order.status == 'COMPLETED':
            raise ValueError("Cannot modify items for a completed order")

        # Build a map of existing item orders by food item ID
        existing_item_orders = {
            io.item.id: io for io in locked_order.item_orders.all()
        }

        # Track which items are in the new data
        updated_items = set()

        for item_data in items_data:
            item_id = item_data['item']
            quantity = item_data['quantity']
            updated_items.add(item_id)

            if item_id in existing_item_orders:
                # Update quantity of existing item order
                item_order = existing_item_orders[item_id]
                item_order.quantity = quantity
                item_order.line_total = quantity * item_order.unit_price
                item_order.save(update_fields=['quantity', 'line_total', 'updated_at'])
            else:
                # Create new item order with current food item price
                food_item = FoodItem.objects.get(id=item_id)
                unit_price = food_item.price
                line_total = quantity * unit_price

                ItemOrder.objects.create(
                    order=locked_order,
                    item=food_item,
                    quantity=quantity,
                    unit_price=unit_price,
                    line_total=line_total
                )

        # Remove items that weren't in the update
        for item_id, item_order in existing_item_orders.items():
            if item_id not in updated_items:
                item_order.delete()

        # Recalculate subtotal after all item changes
        locked_order.subtotal = sum(io.line_total for io in locked_order.item_orders.all())
        locked_order.save(update_fields=['subtotal'])
        order.subtotal = locked_order.subtotal
