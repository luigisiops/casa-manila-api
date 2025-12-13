from rest_framework import serializers
from .models import FoodItem

class FoodItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=50)
    price = serializers.DecimalField(max_digits=6, decimal_places=2)
    size = serializers.CharField(max_length=20)
    category = serializers.CharField(max_length=30, allow_blank=True, allow_null=True, required=False)

    def create(self, validated_data):
        """
        Create and return a new `FoodItem` instance, given the validated data.
        """
        return FoodItem.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update and return an existing `FoodItem` instance, given the validated data.
        """
        instance.name = validated_data.get("name", instance.name)
        instance.price = validated_data.get("price", instance.price)
        instance.size = validated_data.get("size", instance.size)
        instance.category = validated_data.get("category", instance.category)
        instance.save()
        return instance