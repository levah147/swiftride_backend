
"""
FILE LOCATION: analytics/tests/test_analytics.py
"""
from django.test import TestCase
from analytics.utils import calculate_growth_rate, get_demand_level
from decimal import Decimal

class AnalyticsUtilsTest(TestCase):
    def test_calculate_growth_rate(self):
        result = calculate_growth_rate(120, 100)
        self.assertEqual(result, Decimal('20.00'))
    
    def test_get_demand_level(self):
        self.assertEqual(get_demand_level(60), 'peak')
        self.assertEqual(get_demand_level(40), 'high')
        self.assertEqual(get_demand_level(20), 'medium')
        self.assertEqual(get_demand_level(5), 'low')
        
        
        