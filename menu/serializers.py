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
        read_only_fields = ['id']

class OrderSerializer(serializers.ModelSerializer):
    # TODO: Allow nested writes for creating orders with items
    item_orders = ItemOrderSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'pickup_datetime', 'customer_name', 'email', 'phone_number', 'item_orders',
            'total_cost', 'store_id', 'is_completed', 'is_active'
        ]
        read_only_fields = ['id']
