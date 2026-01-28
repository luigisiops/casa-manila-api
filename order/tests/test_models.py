from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from food_item.models import FoodItem
from order.models import Order
from order.services import create_item_order, update_item_order, delete_item_order



class ItemOrderModelTestCase(TestCase):
    def setUp(self):
        self.food_item = FoodItem.objects.create(
            name="Test Item",
            price=Decimal("15.00"),
            size="Regular",
            category="Main"
        )
        self.order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main"
        )

    def test_line_total_calculation_on_save(self):
        """ItemOrder should calculate line_total automatically via service."""

        item_order = create_item_order(
            order=self.order,
            item=self.food_item,
            quantity=3
        )

        self.assertEqual(item_order.line_total, Decimal("45.00"))

    def test_unit_price_locked_at_creation(self):
        """ItemOrder should capture the FoodItem.price at creation and never update it."""

        item = FoodItem.objects.create(
            name="Lock Test Item",
            price=Decimal("10.00"),
            size="Regular"
        )
        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main"
        )

        # Create ItemOrder at price 10.00
        item_order = create_item_order(
            order=order,
            item=item,
            quantity=2
        )

        # Verify unit_price was captured
        self.assertEqual(item_order.unit_price, Decimal("10.00"))
        self.assertEqual(item_order.line_total, Decimal("20.00"))

        # Change the FoodItem price
        item.price = Decimal("25.00")
        item.save()

        # Verify unit_price is still locked
        item_order.refresh_from_db()
        self.assertEqual(item_order.unit_price, Decimal("10.00"))
        self.assertEqual(item_order.line_total, Decimal("20.00"))

    def test_cannot_modify_itemorder_for_completed_order(self):
        """ItemOrder cannot be modified if its order status is COMPLETED."""

        item = FoodItem.objects.create(
            name="Test Item",
            price=Decimal("10.00"),
            size="Regular"
        )
        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main"
        )
        # Create ItemOrder while order is still PLACED
        item_order = create_item_order(
            order=order,
            item=item,
            quantity=1
        )

        # Mark the order as COMPLETED
        order.status = 'COMPLETED'
        order.save()

        # Try to modify quantity on the completed order using service
        with self.assertRaises(ValueError) as context:
            update_item_order(item_order, quantity=2)

        self.assertIn("Cannot modify ItemOrder for a completed order", str(context.exception))

    def test_cannot_create_itemorder_for_completed_order(self):
        """Cannot create a new ItemOrder for an already-completed order."""

        item = FoodItem.objects.create(
            name="Test Item",
            price=Decimal("10.00"),
            size="Regular"
        )
        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main",
            status="COMPLETED"
        )

        # Try to create ItemOrder on completed order using service
        with self.assertRaises(ValueError) as context:
            create_item_order(
                order=order,
                item=item,
                quantity=1
            )

        self.assertIn("Cannot add items to a completed order", str(context.exception))


class OrderModelTestCase(TestCase):
    def test_subtotal_calculation(self):
        """Order should calculate subtotal from all related item orders."""

        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main"
        )

        item1 = FoodItem.objects.create(
            name="Item 1", price=Decimal("10.00"), size="Regular"
        )
        item2 = FoodItem.objects.create(
            name="Item 2", price=Decimal("15.00"), size="Regular"
        )

        create_item_order(order=order, item=item1, quantity=2)
        create_item_order(order=order, item=item2, quantity=1)

        order.refresh_from_db()
        expected_subtotal = (Decimal("10.00") * 2) + (Decimal("15.00") * 1)
        self.assertEqual(order.subtotal, expected_subtotal)

    def test_itemorder_save_updates_order_subtotal(self):
        """Creating or updating an ItemOrder should automatically update the Order subtotal."""

        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main"
        )
        item = FoodItem.objects.create(
            name="Test Item", price=Decimal("20.00"), size="Regular"
        )

        # Create ItemOrder using service
        item_order = create_item_order(order=order, item=item, quantity=2)

        order.refresh_from_db()
        self.assertEqual(order.subtotal, Decimal("40.00"))

        # Update ItemOrder quantity using service
        update_item_order(item_order, quantity=3)

        order.refresh_from_db()
        self.assertEqual(order.subtotal, Decimal("60.00"))

    def test_itemorder_delete_updates_order_subtotal(self):
        """Deleting an ItemOrder should automatically update the Order subtotal."""

        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main"
        )
        item1 = FoodItem.objects.create(
            name="Item 1", price=Decimal("10.00"), size="Regular"
        )
        item2 = FoodItem.objects.create(
            name="Item 2", price=Decimal("15.00"), size="Regular"
        )

        item_order_1 = create_item_order(order=order, item=item1, quantity=2)
        create_item_order(order=order, item=item2, quantity=1)

        order.refresh_from_db()
        self.assertEqual(order.subtotal, Decimal("35.00"))  # (10*2) + 15

        # Delete one item order using service
        delete_item_order(item_order_1)

        order.refresh_from_db()
        self.assertEqual(order.subtotal, Decimal("15.00"))  # Only item2 remains

    def test_itemorder_unit_price_locked_at_creation(self):
        """
        Creating an ItemOrder should capture the FoodItem price at that moment (locked).
        Subsequent FoodItem price changes should not affect the ItemOrder unit_price.
        """

        item = FoodItem.objects.create(
            name="Test Item", price=Decimal("10.00"), size="Regular"
        )

        order1 = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="User 1",
            phone_number="09171111111",
            store_id="main"
        )
        order2 = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="User 2",
            phone_number="09172222222",
            store_id="main"
        )

        # Create first item order at price 10.00
        item_order_1 = create_item_order(order=order1, item=item, quantity=2)
        self.assertEqual(item_order_1.unit_price, Decimal("10.00"))
        self.assertEqual(item_order_1.line_total, Decimal("20.00"))

        # Update the food item price to 15.00
        item.price = Decimal("15.00")
        item.save()

        # Create second item order at new price 15.00
        item_order_2 = create_item_order(order=order2, item=item, quantity=3)
        self.assertEqual(item_order_2.unit_price, Decimal("15.00"))
        self.assertEqual(item_order_2.line_total, Decimal("45.00"))

        # Verify first item order unit_price was NOT changed (still locked at 10.00)
        item_order_1.refresh_from_db()
        self.assertEqual(item_order_1.unit_price, Decimal("10.00"))
        self.assertEqual(item_order_1.line_total, Decimal("20.00"))

        # Verify order subtotals reflect the locked prices
        order1.refresh_from_db()
        order2.refresh_from_db()
        self.assertEqual(order1.subtotal, Decimal("20.00"))
        self.assertEqual(order2.subtotal, Decimal("45.00"))

    def test_cannot_modify_subtotal_of_completed_order(self):
        """Completed orders should have frozen subtotals that cannot be changed."""
        item = FoodItem.objects.create(
            name="Test Item",
            price=Decimal("10.00"),
            size="Regular"
        )
        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main",
            status="COMPLETED",
            subtotal=Decimal("50.00")
        )

        # Try to change subtotal on completed order
        order.subtotal = Decimal("60.00")
        with self.assertRaises(ValueError) as context:
            order.save()

        self.assertIn("Cannot modify subtotal of a completed order", str(context.exception))
