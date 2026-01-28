from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from food_item.models import FoodItem
from orders.models import Order, ItemOrder


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
        from orders.services import create_item_order
        
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
        from orders.services import create_item_order
        
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
        from orders.services import create_item_order
        
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
        from orders.services import create_item_order
        
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
        """ItemOrder should calculate line_total automatically via service."""
        from orders.services import create_item_order
        
        item_order = create_item_order(
            order=self.order,
            item=self.food_item,
            quantity=3
        )

        self.assertEqual(item_order.line_total, Decimal("45.00"))

    def test_unit_price_locked_at_creation(self):
        """ItemOrder should capture the FoodItem.price at creation and never update it."""
        from orders.services import create_item_order
        
        item = FoodItem.objects.create(
            name="Lock Test Item",
            price=Decimal("10.00"),
            size="Regular"
        )
        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main"
        )

        # Create ItemOrder at price 10.00
        item_order = create_item_order(
            order=order,
            item=item,
            quantity=2
        )

        # Verify unit_price was captured
        self.assertEqual(item_order.unit_price, Decimal("10.00"))
        self.assertEqual(item_order.line_total, Decimal("20.00"))

        # Change the FoodItem price
        item.price = Decimal("25.00")
        item.save()

        # Verify unit_price is still locked
        item_order.refresh_from_db()
        self.assertEqual(item_order.unit_price, Decimal("10.00"))
        self.assertEqual(item_order.line_total, Decimal("20.00"))

    def test_cannot_modify_itemorder_for_completed_order(self):
        """ItemOrder cannot be modified if its order status is COMPLETED."""
        from orders.services import create_item_order, update_item_order
        
        item = FoodItem.objects.create(
            name="Test Item",
            price=Decimal("10.00"),
            size="Regular"
        )
        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main"
        )
        # Create ItemOrder while order is still PLACED
        item_order = create_item_order(
            order=order,
            item=item,
            quantity=1
        )

        # Mark the order as COMPLETED
        order.status = 'COMPLETED'
        order.save()

        # Try to modify quantity on the completed order using service
        with self.assertRaises(ValueError) as context:
            update_item_order(item_order, quantity=2)
        
        self.assertIn("Cannot modify ItemOrder for a completed order", str(context.exception))

    def test_cannot_create_itemorder_for_completed_order(self):
        """Cannot create a new ItemOrder for an already-completed order."""
        from orders.services import create_item_order
        
        item = FoodItem.objects.create(
            name="Test Item",
            price=Decimal("10.00"),
            size="Regular"
        )
        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main",
            status="COMPLETED"
        )

        # Try to create ItemOrder on completed order using service
        with self.assertRaises(ValueError) as context:
            create_item_order(
                order=order,
                item=item,
                quantity=1
            )
        
        self.assertIn("Cannot add items to a completed order", str(context.exception))


class OrderModelTestCase(TestCase):
    def test_subtotal_calculation(self):
        """Order should calculate subtotal from all related item orders."""
        from orders.services import create_item_order
        
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

        create_item_order(order=order, item=item1, quantity=2)
        create_item_order(order=order, item=item2, quantity=1)

        order.refresh_from_db()
        expected_subtotal = (Decimal("10.00") * 2) + (Decimal("15.00") * 1)
        self.assertEqual(order.subtotal, expected_subtotal)

    def test_itemorder_save_updates_order_subtotal(self):
        """Creating or updating an ItemOrder should automatically update the Order subtotal."""
        from orders.services import create_item_order, update_item_order
        
        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main"
        )
        item = FoodItem.objects.create(
            name="Test Item", price=Decimal("20.00"), size="Regular"
        )

        # Create ItemOrder using service
        item_order = create_item_order(order=order, item=item, quantity=2)

        order.refresh_from_db()
        self.assertEqual(order.subtotal, Decimal("40.00"))

        # Update ItemOrder quantity using service
        update_item_order(item_order, quantity=3)

        order.refresh_from_db()
        self.assertEqual(order.subtotal, Decimal("60.00"))

    def test_itemorder_delete_updates_order_subtotal(self):
        """Deleting an ItemOrder should automatically update the Order subtotal."""
        from orders.services import create_item_order, delete_item_order
        
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

        item_order_1 = create_item_order(order=order, item=item1, quantity=2)
        create_item_order(order=order, item=item2, quantity=1)

        order.refresh_from_db()
        self.assertEqual(order.subtotal, Decimal("35.00"))  # (10*2) + 15

        # Delete one item order using service
        delete_item_order(item_order_1)

        order.refresh_from_db()
        self.assertEqual(order.subtotal, Decimal("15.00"))  # Only item2 remains

    def test_itemorder_unit_price_locked_at_creation(self):
        """
        Creating an ItemOrder should capture the FoodItem price at that moment (locked).
        Subsequent FoodItem price changes should not affect the ItemOrder unit_price.
        """
        from orders.services import create_item_order
        
        item = FoodItem.objects.create(
            name="Test Item", price=Decimal("10.00"), size="Regular"
        )

        order1 = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="User 1",
            phone_number="09171111111",
            store_id="main"
        )
        order2 = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="User 2",
            phone_number="09172222222",
            store_id="main"
        )

        # Create first item order at price 10.00
        item_order_1 = create_item_order(order=order1, item=item, quantity=2)
        self.assertEqual(item_order_1.unit_price, Decimal("10.00"))
        self.assertEqual(item_order_1.line_total, Decimal("20.00"))

        # Update the food item price to 15.00
        item.price = Decimal("15.00")
        item.save()

        # Create second item order at new price 15.00
        item_order_2 = create_item_order(order=order2, item=item, quantity=3)
        self.assertEqual(item_order_2.unit_price, Decimal("15.00"))
        self.assertEqual(item_order_2.line_total, Decimal("45.00"))
        
        # Verify first item order unit_price was NOT changed (still locked at 10.00)
        item_order_1.refresh_from_db()
        self.assertEqual(item_order_1.unit_price, Decimal("10.00"))
        self.assertEqual(item_order_1.line_total, Decimal("20.00"))

        # Verify order subtotals reflect the locked prices
        order1.refresh_from_db()
        order2.refresh_from_db()
        self.assertEqual(order1.subtotal, Decimal("20.00"))
        self.assertEqual(order2.subtotal, Decimal("45.00"))

    def test_cannot_modify_subtotal_of_completed_order(self):
        """Completed orders should have frozen subtotals that cannot be changed."""
        item = FoodItem.objects.create(
            name="Test Item",
            price=Decimal("10.00"),
            size="Regular"
        )
        order = Order.objects.create(
            pickup_datetime=timezone.now(),
            customer_name="Test User",
            phone_number="09171234567",
            store_id="main",
            status="COMPLETED",
            subtotal=Decimal("50.00")
        )

        # Try to change subtotal on completed order
        order.subtotal = Decimal("60.00")
        with self.assertRaises(ValueError) as context:
            order.save()

        self.assertIn("Cannot modify subtotal of a completed order", str(context.exception))
