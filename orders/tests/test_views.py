from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from food_item.models import FoodItem
from orders.models import Order
from orders.services import create_item_order


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
                "order": self.order.id,
                "item": self.food_item.id,
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
                    {"item": self.item_one.id, "quantity": 2},
                    {"item": self.item_two.id, "quantity": 3},
                ],
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = response.data["id"]
        order = Order.objects.get(id=order)

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
        item_order = create_item_order(
            order=order,
            item=self.item_one,
            quantity=2
        )

        url = reverse("order-detail", args=[order.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        item_order.refresh_from_db()
        self.assertEqual(order.status, 'CANCELLED')
        self.assertFalse(item_order.is_active)

    def test_order_search_by_phone_and_email(self):
        """Search parameter should filter by phone number or email, with phone taking precedence."""
        match_order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Match User",
            email="match@example.com",
            phone_number="09170009999",
            store_id="main"
        )
        Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Other User",
            email="other@example.com",
            phone_number="09178888888",
            store_id="main"
        )

        # Test search by phone number fragment
        url = reverse("order-list")
        response = self.client.get(url, {"search": "0099"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], match_order.id)

        # Test search by email
        response = self.client.get(url, {"search": "match@example.com"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], match_order.id)

        # Test that phone takes precedence over email
        response = self.client.get(url, {"search": "0099+other@example.com"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        # Should match by phone (0099) not email (other@example.com)
        self.assertEqual(response.data["results"][0]["id"], match_order.id)

    def test_order_filter_by_date_and_search(self):
        """Filtering by pickup_date and search should work together."""
        today = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        # Order matching both date and phone
        match_order = Order.objects.create(
            pickup_datetime=today,
            customer_name="Match User",
            email="match@example.com",
            phone_number="09170009999",
            store_id="main"
        )
        # Order with same phone but different date
        Order.objects.create(
            pickup_datetime=tomorrow,
            customer_name="Same Phone User",
            email="samphone@example.com",
            phone_number="09170009999",
            store_id="main"
        )
        # Order with same date but different phone
        Order.objects.create(
            pickup_datetime=today,
            customer_name="Same Date User",
            email="samedate@example.com",
            phone_number="09178888888",
            store_id="main"
        )

        url = reverse("order-list")

        # Filter by both date and phone search
        response = self.client.get(url, {
            "pickup_date": today.date().isoformat(),
            "search": "0099"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], match_order.id)

        # Filter by date and email search
        response = self.client.get(url, {
            "pickup_date": today.date().isoformat(),
            "search": "match@example.com"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], match_order.id)

    def test_invalid_pickup_date_returns_400(self):
        """Invalid pickup_date should return a clear 400 error."""
        Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09170009999",
            store_id="main",
        )

        url = reverse("order-list")
        response = self.client.get(url, {"pickup_date": "2024-13-40"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pickup_date", response.data)
        self.assertIn("Invalid date format", str(response.data["pickup_date"]))

    def test_full_update_order(self):
        """Full update (PUT) of an Order should update all fields."""
        
        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Original Name",
            email="original@example.com",
            phone_number="09170001111",
            store_id="main"
        )
        create_item_order(order=order, item=self.item_one, quantity=2)

        url = reverse("order-detail", args=[order.id])
        new_pickup_time = timezone.now() + timedelta(days=1)

        response = self.client.put(
            url,
            {
                "pickup_datetime": new_pickup_time.isoformat(),
                "customer_name": "Updated Name",
                "email": "updated@example.com",
                "phone_number": "09170002222",
                "store_id": "branch-2",
                "is_completed": False,
                "is_active": True,
                "items": []  # Empty items list for this test
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.customer_name, "Updated Name")
        self.assertEqual(order.email, "updated@example.com")
        self.assertEqual(order.phone_number, "09170002222")
        self.assertEqual(order.store_id, "branch-2")

    def test_partial_update_order_phone_only(self):
        """Partial update (PATCH) should only update specified fields."""
        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Original Name",
            email="original@example.com",
            phone_number="09170001111",
            store_id="main"
        )

        url = reverse("order-detail", args=[order.id])
        response = self.client.patch(
            url,
            {"phone_number": "09170005555"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.phone_number, "09170005555")
        # Other fields should remain unchanged
        self.assertEqual(order.customer_name, "Original Name")
        self.assertEqual(order.email, "original@example.com")

    def test_update_order_with_item_list_recalculates_subtotal(self):
        """Updating an order's items should recalculate the subtotal."""
        
        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main"
        )
        # Create initial item orders
        create_item_order(order=order, item=self.item_one, quantity=1)
        create_item_order(order=order, item=self.item_two, quantity=1)

        order.refresh_from_db()
        initial_subtotal = order.subtotal
        self.assertEqual(initial_subtotal, Decimal("20.75"))  # 12.50 + 8.25

        # Update item quantities through PATCH
        url = reverse("order-detail", args=[order.id])
        response = self.client.patch(
            url,
            {
                "items": [
                    {"item": self.item_one.id, "quantity": 3},
                    {"item": self.item_two.id, "quantity": 2},
                ]
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        # New subtotal: (12.50 * 3) + (8.25 * 2) = 37.50 + 16.50 = 54.00
        self.assertEqual(order.subtotal, Decimal("54.00"))

    def test_removing_items_from_order_updates_subtotal(self):
        """Removing an item from an order should update the subtotal."""
        
        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main"
        )
        create_item_order(order=order, item=self.item_one, quantity=2)
        create_item_order(order=order, item=self.item_two, quantity=1)

        order.refresh_from_db()
        initial_subtotal = order.subtotal
        self.assertEqual(initial_subtotal, Decimal("33.25"))  # (12.50 * 2) + 8.25

        # Remove the second item via PATCH (only keep first item)
        url = reverse("order-detail", args=[order.id])
        response = self.client.patch(
            url,
            {
                "items": [
                    {"item": self.item_one.id, "quantity": 2}
                ]
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        # New subtotal: 12.50 * 2 = 25.00
        self.assertEqual(order.subtotal, Decimal("25.00"))
