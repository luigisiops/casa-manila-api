from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ItemOrderViewSet, OrderViewSet

router = DefaultRouter()
router.register(r'item-orders', ItemOrderViewSet)
router.register(r'orders', OrderViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
