from django.db import models, transaction
from django.core.validators import MinValueValidator
from food_item.models import FoodItem


class Order(models.Model):
    pickup_datetime = models.DateTimeField(null=False, blank=False, db_index=True)
    customer_name = models.CharField(max_length=50, null=False, blank=False)
    email = models.CharField(max_length=50, blank=True, null=True)
    phone_number = models.CharField(max_length=15)
    subtotal = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    store_id = models.CharField(max_length=20, help_text="One of two possible locations")
    # TODO: add Status ENUM with (Active, Completed, Cancelled)
    is_completed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_subtotal(self):
        """Calculate and update subtotal from related item orders."""
        self.subtotal = sum(item.line_total for item in self.item_orders.all())

    class Meta:
        ordering = ["pickup_datetime"]


class ItemOrder(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="item_orders")
    item = models.ForeignKey(FoodItem, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.IntegerField(
        default=1, null=False, blank=False, validators=[MinValueValidator(1)]
    )
    line_total = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Ensure line_total and order subtotal updates are atomic and serialized per order
        with transaction.atomic():
            # Acquire a row-level lock on the related order to prevent concurrent subtotal races
            order = Order.objects.select_for_update().get(pk=self.order.pk)
            self.line_total = self.quantity * self.item.price
            super().save(*args, **kwargs)
            # Recalculate and persist the locked order's subtotal
            order.calculate_subtotal()
            order.save(update_fields=['subtotal'])

    def delete(self, *args, **kwargs):
        # Ensure deletion and subtotal recalculation are atomic and serialized per order
        with transaction.atomic():
            # Lock the related order row to avoid concurrent subtotal races
            order = Order.objects.select_for_update().get(pk=self.order.pk)
            super().delete(*args, **kwargs)
            # Recalculate and persist the locked order's subtotal after deletion
            order.calculate_subtotal()
            order.save(update_fields=['subtotal'])

    class Meta:
        ordering = ["created_at"]
