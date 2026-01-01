from rest_framework import serializers
from .models import FoodItem, Order, ItemOrder

class FoodItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodItem
        fields = ['id', 'name', 'price', 'size', 'category', 'is_active']
        read_only_fields = ['id']

class ItemOrderSerializer(serializers.ModelSerializer):
    food_item = FoodItemSerializer(source='item_id', read_only=True)

    class Meta:
        model = ItemOrder
        fields = ['id', 'order_id', 'food_item', 'item_id', 'quantity', 'is_active']
        read_only_fields = ['id', 'order_id']

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
            'total_cost', 'store_id', 'is_completed', 'is_active',
            'item_orders', 'items'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        order = Order.objects.create(**validated_data)
        
        for item_data in items_data:
            ItemOrder.objects.create(
                order_id=order,
                item_id_id=item_data['item_id'],
                quantity=item_data['quantity']
            )
        
        return order
