# Import all test classes to ensure test discovery works
from orders.tests.test_views import ItemOrderViewSetTestCase, OrderViewSetTestCase
from orders.tests.test_models import ItemOrderModelTestCase, OrderModelTestCase

__all__ = [
    'ItemOrderViewSetTestCase',
    'OrderViewSetTestCase',
    'ItemOrderModelTestCase',
    'OrderModelTestCase',
]
