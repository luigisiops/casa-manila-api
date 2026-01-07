from rest_framework import serializers
from menu.models import FoodItem, Order, ItemOrder

class FoodItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodItem
        fields = ['id', 'name', 'price', 'size', 'category', 'is_active']
        read_only_fields = ['id']

class ItemOrderSerializer(serializers.ModelSerializer):
    food_item = FoodItemSerializer(source='item_id', read_only=True)

    class Meta:
        model = ItemOrder
        fields = ['id', 'order_id', 'food_item', 'item_id', 'quantity', 'line_total', 'is_active']
        read_only_fields = ['id', 'order_id', 'line_total']

class OrderSerializer(serializers.ModelSerializer):
    item_orders = ItemOrderSerializer(many=True, read_only=True)
    # Accept simple item_id and quantity for creation
    items = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )

    class Meta:
        model = Order
        fields = [
            'id', 'pickup_datetime', 'customer_name', 'email', 'phone_number',
            'subtotal', 'store_id', 'is_completed', 'is_active',
            'item_orders', 'items'
        ]
        read_only_fields = ['id', 'subtotal']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        order = Order.objects.create(**validated_data)

        for item_data in items_data:
            ItemOrder.objects.create(
                order_id=order,
                item_id_id=item_data['item_id'],
                quantity=item_data['quantity']
            )

        # Recalculate subtotal after items are created
        order.calculate_subtotal()
        order.save(update_fields=['subtotal'])

        return order

    def update(self, instance, validated_data):
        from django.db import transaction

        items_data = validated_data.pop('items', None)

        with transaction.atomic():
            # Update order fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            # If items were provided, update the item orders
            if items_data is not None:
                # Get existing item orders
                existing_item_orders = {io.item_id.id: io for io in instance.item_orders.all()}

                # Track which items are in the new data
                updated_item_ids = set()

                for item_data in items_data:
                    item_id = item_data['item_id']
                    quantity = item_data['quantity']
                    updated_item_ids.add(item_id)

                    if item_id in existing_item_orders:
                        # Update existing item order
                        item_order = existing_item_orders[item_id]
                        item_order.quantity = quantity
                        item_order.save()
                    else:
                        # Create new item order
                        ItemOrder.objects.create(
                            order_id=instance,
                            item_id_id=item_id,
                            quantity=quantity
                        )

                # Remove items that weren't in the update
                for item_id, item_order in existing_item_orders.items():
                    if item_id not in updated_item_ids:
                        item_order.delete()

                # Recalculate subtotal
                instance.refresh_from_db()
                instance.calculate_subtotal()
                instance.save(update_fields=['subtotal'])

        return instance
