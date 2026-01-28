from django.db import models
from django.core.validators import MinValueValidator
from food_item.models import FoodItem


class Order(models.Model):
    STATUS_CHOICES = [
        ('PLACED', 'Placed'),
        ('IN_PROGRESS', 'In Progress'),
        ('READY', 'Ready'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    pickup_datetime = models.DateTimeField(null=False, blank=False, db_index=True)
    customer_name = models.CharField(max_length=50, null=False, blank=False)
    email = models.CharField(max_length=50, blank=True, null=True)
    phone_number = models.CharField(max_length=15)
    subtotal = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    store_id = models.CharField(max_length=20, help_text="One of two possible locations")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PLACED',
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Prevent direct subtotal modification of completed orders
        if self.pk:
            existing = Order.objects.get(pk=self.pk)
            if existing.status == 'COMPLETED' and self.status == 'COMPLETED':
                if existing.subtotal != self.subtotal:
                    raise ValueError("Cannot modify subtotal of a completed order")

        super().save(*args, **kwargs)

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
    unit_price = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        help_text="Price of the item at the time of ordering (locked)"
    )
    line_total = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
