from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from menu.models import FoodItem, Order, ItemOrder


class FoodItemViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.active_item_1 = FoodItem.objects.create(
            name="Active 1",
            price=Decimal("10.00"),
            size="Regular",
            category="Main",
            is_active=True
        )
        self.active_item_2 = FoodItem.objects.create(
            name="Active 2",
            price=Decimal("12.00"),
            size="Large",
            category="Main",
            is_active=True
        )
        self.inactive_item = FoodItem.objects.create(
            name="Inactive",
            price=Decimal("8.00"),
            size="Regular",
            category="Main",
            is_active=False
        )

    def test_list_filters_active_by_default(self):
        """List endpoint should only return active items by default."""
        url = reverse("fooditem-list")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        for item in response.data["results"]:
            self.assertTrue(item["is_active"])

    def test_list_includes_inactive_with_flag(self):
        """List endpoint should include inactive items when flag is set."""
        url = reverse("fooditem-list")
        response = self.client.get(url, {"include_inactive": "true"})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)

    def test_soft_delete_marks_inactive(self):
        """DELETE should archive the item by marking it inactive."""
        url = reverse("fooditem-detail", args=[self.active_item_1.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.active_item_1.refresh_from_db()
        self.assertFalse(self.active_item_1.is_active)


class ItemOrderViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.food_item = FoodItem.objects.create(
            name="Adobo",
            price=Decimal("10.00"),
            size="Regular",
            category="Main"
        )
        self.order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Juan Dela Cruz",
            phone_number="09171234567",
            store_id="main"
        )

    def test_viewset_is_read_only(self):
        """ItemOrder endpoint should not allow POST requests."""
        url = reverse("itemorder-list")
        response = self.client.post(
            url,
            {
                "order_id": self.order.id,
                "item_id": self.food_item.id,
                "quantity": 1
            },
            format="json"
        )
        
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class OrderViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.item_one = FoodItem.objects.create(
            name="Lumpia",
            price=Decimal("12.50"),
            size="Regular",
            category="Appetizer"
        )
        self.item_two = FoodItem.objects.create(
            name="Pancit",
            price=Decimal("8.25"),
            size="Regular",
            category="Main"
        )

    def test_order_creation_creates_items_and_subtotal(self):
        """Creating an order with items should calculate subtotal correctly."""
        url = reverse("order-list")
        pickup_time = timezone.now() + timedelta(hours=2)
        
        response = self.client.post(
            url,
            {
                "pickup_datetime": pickup_time.isoformat(),
                "customer_name": "Maria Clara",
                "email": "maria@example.com",
                "phone_number": "09170001111",
                "store_id": "branch-1",
                "items": [
                    {"item_id": self.item_one.id, "quantity": 2},
                    {"item_id": self.item_two.id, "quantity": 3},
                ],
            },
            format="json"
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order_id = response.data["id"]
        order = Order.objects.get(id=order_id)
        
        expected_subtotal = (Decimal("12.50") * 2) + (Decimal("8.25") * 3)
        self.assertEqual(order.item_orders.count(), 2)
        self.assertEqual(order.subtotal, expected_subtotal)

    def test_order_destroy_archives_order_and_items(self):
        """DELETE should archive order and all related item orders."""
        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main"
        )
        item_order = ItemOrder.objects.create(
            order_id=order,
            item_id=self.item_one,
            quantity=2
        )
        
        url = reverse("order-detail", args=[order.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        item_order.refresh_from_db()
        self.assertFalse(order.is_active)
        self.assertFalse(item_order.is_active)

    def test_order_search_by_date_and_phone_fragment(self):
        """Search parameter should filter by date and phone number."""
        target_dt = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        match_order = Order.objects.create(
            pickup_datetime=target_dt,
            customer_name="Match User",
            phone_number="09170009999",
            store_id="main"
        )
        Order.objects.create(
            pickup_datetime=target_dt + timedelta(days=1),
            customer_name="Other User",
            phone_number="09178888888",
            store_id="main"
        )
        
        search_term = f"{target_dt.date().isoformat()}+0099"
        url = reverse("order-list")
        response = self.client.get(url, {"search": search_term})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], match_order.id)


class ItemOrderModelTestCase(TestCase):
    def setUp(self):
        self.food_item = FoodItem.objects.create(
            name="Test Item",
            price=Decimal("15.00"),
            size="Regular",
            category="Main"
        )
        self.order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main"
        )

    def test_line_total_calculation_on_save(self):
        """ItemOrder should calculate line_total automatically on save."""
        item_order = ItemOrder(
            order_id=self.order,
            item_id=self.food_item,
            quantity=3
        )
        item_order.save()
        
        self.assertEqual(item_order.line_total, Decimal("45.00"))


class OrderModelTestCase(TestCase):
    def test_subtotal_calculation(self):
        """Order should calculate subtotal from all related item orders."""
        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main"
        )
        
        item1 = FoodItem.objects.create(
            name="Item 1", price=Decimal("10.00"), size="Regular"
        )
        item2 = FoodItem.objects.create(
            name="Item 2", price=Decimal("15.00"), size="Regular"
        )
        
        ItemOrder.objects.create(order_id=order, item_id=item1, quantity=2)
        ItemOrder.objects.create(order_id=order, item_id=item2, quantity=1)
        
        order.calculate_subtotal()
        order.save(update_fields=["subtotal"])
        
        expected_subtotal = (Decimal("10.00") * 2) + (Decimal("15.00") * 1)
        self.assertEqual(order.subtotal, expected_subtotal)
