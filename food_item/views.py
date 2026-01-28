from rest_framework import viewsets, status
from rest_framework.response import Response
from food_item.models import FoodItem
from food_item.serializers import FoodItemSerializer


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
