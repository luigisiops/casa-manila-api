from django.db import models
from django.core.validators import MinValueValidator

class FoodItem(models.Model):
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    size = models.CharField(max_length=20)
    category = models.CharField(max_length=30, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    # TODO: Implement Soft-delete as deleted_at
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)      
    class Meta:
        ordering = ["name"]

class Order(models.Model):
    pickup_datetime = models.DateTimeField(null=False, blank=False, db_index=True)
    customer_name = models.CharField(max_length=50, null=False, blank=False)
    email = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=15)
    total_cost = models.DecimalField(max_digits=6, decimal_places=2)
    store_id = models.CharField(max_length=20, help_text="One of two possible locations")
    # TODO: add Status ENUM with (Active, Completed, Cancelled)
    is_completed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ItemOrder(models.Model):
    order_id = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="item_orders")
    item_id = models.ForeignKey(FoodItem, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.IntegerField(
        default=1, null=False, blank=False, validators=[MinValueValidator(1)]
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
