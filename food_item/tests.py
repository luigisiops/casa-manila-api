from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from food_item.models import FoodItem
from orders.models import Order


class FoodItemViewSetTestCase(TestCase):
    def setUp(self):
        from orders.services import create_item_order
        
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
        # Create an order with items for testing price updates
        self.order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main"
        )
        self.item_order = create_item_order(
            order=self.order,
            item=self.active_item_1,
            quantity=2
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

    def test_full_update_fooditem(self):
        """Full update (PUT) of a FoodItem should update all fields."""
        url = reverse("fooditem-detail", args=[self.active_item_1.id])
        response = self.client.put(
            url,
            {
                "name": "Updated Name",
                "price": Decimal("25.00"),
                "size": "Extra Large",
                "category": "Premium",
                "is_active": True
            },
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.active_item_1.refresh_from_db()
        self.assertEqual(self.active_item_1.name, "Updated Name")
        self.assertEqual(self.active_item_1.price, Decimal("25.00"))
        self.assertEqual(self.active_item_1.size, "Extra Large")
        self.assertEqual(self.active_item_1.category, "Premium")

    def test_partial_update_fooditem(self):
        """Partial update (PATCH) of a FoodItem should only update specified fields."""
        url = reverse("fooditem-detail", args=[self.active_item_1.id])
        response = self.client.patch(
            url,
            {"name": "Partially Updated"},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.active_item_1.refresh_from_db()
        self.assertEqual(self.active_item_1.name, "Partially Updated")
        # Other fields should remain unchanged
        self.assertEqual(self.active_item_1.price, Decimal("10.00"))
        self.assertEqual(self.active_item_1.size, "Regular")

    def test_price_update_does_not_affect_existing_orders(self):
        """Updating FoodItem price should NOT update existing item orders 
        (prices locked at order time)."""
        # Setup: Verify initial state
        self.item_order.refresh_from_db()
        self.order.refresh_from_db()
        initial_line_total = self.item_order.line_total
        initial_subtotal = self.order.subtotal

        self.assertEqual(initial_line_total, Decimal("20.00"))  # 10.00 * 2
        self.assertEqual(initial_subtotal, Decimal("20.00"))
        self.assertEqual(self.item_order.unit_price, Decimal("10.00"))

        # Update the price via API
        url = reverse("fooditem-detail", args=[self.active_item_1.id])
        response = self.client.patch(
            url,
            {"price": Decimal("15.00")},
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify that item order line total and order subtotal are NOT changed
        self.item_order.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.item_order.line_total, Decimal("20.00"))  # Still 10.00 * 2
        self.assertEqual(self.item_order.unit_price, Decimal("10.00"))  # Unit price locked
        self.assertEqual(self.order.subtotal, Decimal("20.00"))  # Subtotal unchanged
