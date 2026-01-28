# Import all test classes to ensure test discovery works
from order.tests.test_views import ItemOrderViewSetTestCase, OrderViewSetTestCase
from order.tests.test_models import ItemOrderModelTestCase, OrderModelTestCase

__all__ = [
    'ItemOrderViewSetTestCase',
    'OrderViewSetTestCase',
    'ItemOrderModelTestCase',
    'OrderModelTestCase',
]
