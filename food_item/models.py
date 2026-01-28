from django.db import models, transaction


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
                # Edge case: object was deleted after being loaded
                # Treat as new object with no price change
                pass

        super().save(*args, **kwargs)

        # If price changed, update all related item orders and their orders
        if price_changed:
            # Import here to avoid circular dependency
            from orders.models import Order
            
            with transaction.atomic():
                # Update all related item order line_totals in a single query
                item_orders_qs = self.order_items.all()
                item_orders_qs.update(
                    line_total=models.F("quantity") * self.price
                )
                # Recalculate subtotals for affected orders in bulk
                order_totals = item_orders_qs.values("order").annotate(
                    subtotal=models.Sum("line_total")
                )
                orders = [ot["order"] for ot in order_totals]
                if orders:
                    orders_by_id = {
                        order.id: order
                        for order in Order.objects.filter(id__in=orders)
                    }
                    for ot in order_totals:
                        order = orders_by_id.get(ot["order"])
                        if order is not None:
                            # Default to 0 if subtotal is None
                            order.subtotal = ot["subtotal"] or 0
                    Order.objects.bulk_update(
                        list(orders_by_id.values()),
                        ["subtotal"],
                    )

    class Meta:
        ordering = ["name"]
