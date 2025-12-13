from django.db import models

class FoodItem(models.Model):
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    size = models.CharField(max_length=20)
    category = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        ordering = ["name"]