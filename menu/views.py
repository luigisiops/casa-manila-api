import re
from datetime import datetime
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.response import Response
from menu.models import FoodItem, ItemOrder, Order
from menu.serializers import FoodItemSerializer, ItemOrderSerializer, OrderSerializer


class ActiveFilterMixin:
    """Helper to default list endpoints to active records unless opted out."""

    def filter_active(self, qs):
        include_inactive = self.request.query_params.get("include_inactive")
        include_inactive = str(include_inactive).lower() in {"1", "true", "yes"}
        if not include_inactive:
            qs = qs.filter(is_active=True)
        return qs


class FoodItemViewSet(ActiveFilterMixin, viewsets.ModelViewSet):
    queryset = FoodItem.objects.all()
    serializer_class = FoodItemSerializer

    def get_queryset(self):
        """Default to active items; allow include_inactive override."""
        return self.filter_active(super().get_queryset())

    def destroy(self, request, *args, **kwargs):
        """
        Archives the food item by marking it as inactive.
        """
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(
            {'detail': 'Item archived successfully'},
            status=status.HTTP_200_OK
        )

class ItemOrderViewSet(ActiveFilterMixin, viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for ItemOrders.
    ItemOrders can only be created through the Order endpoint.
    """
    queryset = ItemOrder.objects.all()
    serializer_class = ItemOrderSerializer

    def get_queryset(self):
        """Default to active item-orders; allow include_inactive override."""
        return self.filter_active(super().get_queryset())

class OrderViewSet(ActiveFilterMixin, viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_queryset(self):
        """Allow filtering by pickup date/phone; default to active orders only."""
        qs = self.filter_active(super().get_queryset())
        params = self.request.query_params

        pickup_date = params.get("pickup_date")
        phone_number = params.get("phone_number")
        search = params.get("search")

        # Parse combined search like "2024-01-01+0917" into date/phone parts.
        if search:
            tokens = [t for t in re.split(r"[ +]+", search) if t]
            for token in tokens:
                # Treat valid YYYY-MM-DD as pickup date, everything else as phone fragment.
                try:
                    datetime.strptime(token, "%Y-%m-%d")
                    pickup_date = pickup_date or token
                    continue
                except ValueError:
                    phone_number = phone_number or token

        if pickup_date:
            try:
                qs = qs.filter(pickup_datetime__date=datetime.strptime(pickup_date, "%Y-%m-%d"))
            except ValueError:
                pass  # Ignore invalid date format and return unfiltered set.

        if phone_number:
            qs = qs.filter(phone_number__icontains=phone_number)

        return qs

    def destroy(self, request, *args, **kwargs):
        """
        Archives the order by marking it and its item orders as inactive.
        """
        with transaction.atomic():
            instance = self.get_object()
            instance.is_active = False
            instance.save(update_fields=["is_active"])
            instance.item_orders.update(is_active=False)
        return Response(
            {'detail': 'Order and item orders archived successfully'},
            status=status.HTTP_200_OK
        )
