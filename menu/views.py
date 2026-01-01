from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import FoodItem, ItemOrder, Order
from .serializers import FoodItemSerializer, ItemOrderSerializer, OrderSerializer


class FoodItemViewSet(viewsets.ModelViewSet):
    queryset = FoodItem.objects.all()
    serializer_class = FoodItemSerializer

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

class ItemOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for ItemOrders.
    ItemOrders can only be created through the Order endpoint.
    """
    queryset = ItemOrder.objects.all()
    serializer_class = ItemOrderSerializer

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

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
