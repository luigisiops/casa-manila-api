from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import FoodItem
from .serializers import FoodItemSerializer


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
