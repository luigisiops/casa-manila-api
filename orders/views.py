import re
from datetime import datetime
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from orders.models import ItemOrder, Order
from orders.serializers import ItemOrderSerializer, OrderSerializer


class ActiveFilterMixin:
    """Helper to default list endpoints to active records unless opted out."""

    def filter_active(self, qs):
        include_inactive = self.request.query_params.get("include_inactive")
        include_inactive = str(include_inactive).lower() in {"1", "true", "yes"}
        if not include_inactive:
            qs = qs.filter(is_active=True)
        return qs


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
        """Allow filtering by pickup date/phone/email; default to active orders only."""
        qs = self.filter_active(super().get_queryset())
        params = self.request.query_params

        pickup_date = params.get("pickup_date")
        phone_number = params.get("phone_number")
        email = params.get("email")
        search = params.get("search")

        # Parse combined search string to extract phone and email.
        # Example: "0917+user@example.com"
        if search:
            tokens = [t for t in re.split(r"[ +]+", search) if t]
            for token in tokens:
                # Check if token is an email (contains @)
                if "@" in token:
                    email = email or token
                # Otherwise, treat as phone number
                else:
                    phone_number = phone_number or token

        # Apply date filter if specified
        if pickup_date:
            try:
                parsed_date = datetime.strptime(pickup_date, "%Y-%m-%d")
            except ValueError as exc:
                raise ValidationError(
                    {"pickup_date": "Invalid date format. Use YYYY-MM-DD."}
                ) from exc

            qs = qs.filter(pickup_datetime__date=parsed_date)

        # Apply phone/email filter with phone number having precedence
        if phone_number:
            qs = qs.filter(phone_number__icontains=phone_number)
        elif email:
            qs = qs.filter(email__icontains=email)

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
