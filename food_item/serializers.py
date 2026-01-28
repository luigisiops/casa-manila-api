from rest_framework import serializers
from food_item.models import FoodItem


class FoodItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodItem
        fields = ['id', 'name', 'price', 'size', 'category', 'is_active']
        read_only_fields = ['id', 'is_active']
