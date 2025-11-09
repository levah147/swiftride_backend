"""
FILE LOCATION: promotions/tests/test_promos.py
"""
from django.test import TestCase
from promotions.models import PromoCode
from decimal import Decimal

class PromoCodeTest(TestCase):
    def test_calculate_discount(self):
        promo = PromoCode(discount_type='percentage', discount_value=Decimal('20'))
        discount = promo.calculate_discount(Decimal('1000'))
        self.assertEqual(discount, Decimal('200'))


