from rest_framework import serializers
from order.models import Order, ItemOrder
from order.services import create_order_with_items, add_or_update_order_items
from food_item.serializers import FoodItemSerializer


class ItemOrderSerializer(serializers.ModelSerializer):
    food_item = FoodItemSerializer(source='item', read_only=True)

    class Meta:
        model = ItemOrder
        fields = [
            'id', 'order', 'food_item', 'item', 'quantity', 'unit_price', 'line_total', 'is_active'
        ]
        read_only_fields = ['id', 'order', 'unit_price', 'line_total']


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
        """Create an order with items using the service layer."""
        return create_order_with_items(validated_data)

    def update(self, instance, validated_data):
        """Update an order using the service layer for item management."""
        items_data = validated_data.pop('items', None)

        # Update order fields directly
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If items were provided, update them using the service
        if items_data is not None:
            add_or_update_order_items(instance, items_data)
            instance.refresh_from_db()

        return instance
