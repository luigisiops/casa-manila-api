from rest_framework import serializers
from orders.models import Order, ItemOrder
from food_item.serializers import FoodItemSerializer


class ItemOrderSerializer(serializers.ModelSerializer):
    food_item = FoodItemSerializer(source='item', read_only=True)

    class Meta:
        model = ItemOrder
        fields = ['id', 'order', 'food_item', 'item', 'quantity', 'line_total', 'is_active']
        read_only_fields = ['id', 'order', 'line_total']


class OrderItemInputSerializer(serializers.Serializer):
    item = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class OrderSerializer(serializers.ModelSerializer):
    item_orders = ItemOrderSerializer(many=True, read_only=True)
    # Accept simple item and quantity for creation
    items = OrderItemInputSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Order
        fields = [
            'id', 'pickup_datetime', 'customer_name', 'email', 'phone_number',
            'subtotal', 'store_id', 'status',
            'item_orders', 'items'
        ]
        read_only_fields = ['id', 'subtotal', 'status']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        order = Order.objects.create(**validated_data)

        for item_data in items_data:
            ItemOrder.objects.create(
                order=order,
                item_id=item_data['item'],
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
                existing_item_orders = {io.item.id: io for io in instance.item_orders.all()}

                # Track which items are in the new data
                updated_items = set()

                for item_data in items_data:
                    item = item_data['item']
                    quantity = item_data['quantity']
                    updated_items.add(item)

                    if item in existing_item_orders:
                        # Update existing item order
                        item_order = existing_item_orders[item]
                        item_order.quantity = quantity
                        item_order.save()
                    else:
                        # Create new item order
                        ItemOrder.objects.create(
                            order=instance,
                            item_id=item,
                            quantity=quantity
                        )

                # Remove items that weren't in the update
                for item, item_order in existing_item_orders.items():
                    if item not in updated_items:
                        item_order.delete()

                # Recalculate subtotal
                instance.refresh_from_db()
                instance.calculate_subtotal()
                instance.save(update_fields=['subtotal'])

        return instance
