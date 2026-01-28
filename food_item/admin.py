from django.contrib import admin
from food_item.models import FoodItem


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price', 'size', 'category', 'is_active']
    list_filter = ['is_active', 'category', 'size']
    search_fields = ['name', 'category']
    readonly_fields = ['created_at', 'updated_at']
