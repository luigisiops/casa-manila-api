import re
from datetime import datetime
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from order.models import ItemOrder, Order
from order.serializers import ItemOrderSerializer, OrderSerializer
from order.validators import validate_email_format, validate_phone_format


class ItemOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for ItemOrders.
    ItemOrders can only be created through the Order endpoint.
    """
    queryset = ItemOrder.objects.all()
    serializer_class = ItemOrderSerializer

    def get_queryset(self):
        """Default to active items only; allow include_inactive override."""
        qs = super().get_queryset()
        params = self.request.query_params

        # Default to active items; include inactive if explicitly requested
        include_inactive = params.get("include_inactive")
        include_inactive = str(include_inactive).lower() in {"1", "true", "yes"}
        if not include_inactive:
            qs = qs.filter(is_active=True)

        return qs


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_queryset(self):
        """Allow filtering by pickup date/phone/email; default to active orders only."""
        qs = super().get_queryset()
        params = self.request.query_params

        # Default to active orders unless explicitly requested otherwise
        include_inactive = params.get("include_inactive")
        include_inactive = str(include_inactive).lower() in {"1", "true", "yes"}
        if not include_inactive:
            qs = qs.exclude(status='CANCELLED')

        pickup_date = params.get("pickup_date")
        phone_number = params.get("phone_number")
        email = params.get("email")
        search = params.get("search")
        status_filter = params.get("status")

        # Parse combined search string to extract phone and email.
        # Example: "0917+user@example.com"
        if search:
            tokens = [t for t in re.split(r"[ +]+", search) if t]
            for token in tokens:
                # Check if token is an email (contains @)
                if "@" in token:
                    validated_email = validate_email_format(token)
                    email = email or validated_email
                # Otherwise, treat as phone number
                else:
                    validated_phone = validate_phone_format(token)
                    phone_number = phone_number or validated_phone

        # Apply date filter if specified
        if pickup_date:
            try:
                parsed_date = datetime.strptime(pickup_date, "%Y-%m-%d")
            except ValueError as exc:
                raise ValidationError(
                    {"pickup_date": "Invalid date format. Use YYYY-MM-DD."}
                ) from exc

            qs = qs.filter(pickup_datetime__date=parsed_date)

        # Apply status filter if specified
        if status_filter:
            qs = qs.filter(status=status_filter)

        # Apply phone/email filter with phone number having precedence
        if phone_number:
            qs = qs.filter(phone_number__icontains=phone_number)
        elif email:
            qs = qs.filter(email__icontains=email)

        return qs

    def destroy(self, request, *args, **kwargs):
        """
        Cancels the order by setting status to CANCELLED and marking item orders as inactive.
        """
        instance = self.get_object()
        instance.status = 'CANCELLED'
        instance.save(update_fields=['status'])
        instance.item_orders.update(is_active=False)
        return Response(
            {'detail': 'Order cancelled successfully'},
            status=status.HTTP_200_OK
        )
