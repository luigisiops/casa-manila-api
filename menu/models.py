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

    def save(self, *args, **kwargs):
        # Track price changes to update related orders
        price_changed = False
        if self.pk:
            try:
                original = FoodItem.objects.get(pk=self.pk)
                price_changed = original.price != self.price
            except FoodItem.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        # If price changed, update all related item orders and their orders
        if price_changed:
            from django.db import transaction
            with transaction.atomic():
                item_orders = self.order_items.all()
                for item_order in item_orders:
                    item_order.line_total = item_order.quantity * self.price
                    item_order.save(update_fields=['line_total'])
                    # Recalculate the order's subtotal
                    item_order.order.calculate_subtotal()
                    item_order.order.save(update_fields=['subtotal'])

    class Meta:
        ordering = ["name"]

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

    def save(self, *args, **kwargs):
        # Skip calculation on creation (no items exist yet)
        if self.pk:
            self.calculate_subtotal()
        super().save(*args, **kwargs)

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
        self.line_total = self.quantity * self.item.price
        super().save(*args, **kwargs)
        # Recalculate the parent order's subtotal
        self.order.calculate_subtotal()
        self.order.save(update_fields=['subtotal'])

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        # Recalculate the parent order's subtotal after deletion
        order.calculate_subtotal()
        order.save(update_fields=['subtotal'])

    class Meta:
        ordering = ["created_at"]
