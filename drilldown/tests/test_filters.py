from collections import OrderedDict
from copy import copy
from unittest.mock import MagicMock

from django.http import QueryDict
from django.test import TestCase

from drilldown.filters import ChoiceFilter, AgeFilter, filters_from_request


class FiltersTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.test_filters = [
            ChoiceFilter(
                choices=[
                    ('1', 'one', 'one person'),
                    ('2', 'two', 'two people'),
                ],
                display_name='number',
                field_name='num',
            ),
            ChoiceFilter(
                choices=[
                    ('S', 'spaces', 'who indent with spaces'),
                    ('T', 'tabs', 'who indent with tabs'),
                ],
                display_name="indenting",
                field_name="indent",

            ),
            AgeFilter(),
        ]


class ChoiceFilterTest(FiltersTest):
    def test_choice_filter_constructor_validation(self):
        with self.assertRaises(ValueError):
            # Choices list must not be empty
            ChoiceFilter(choices=[], display_name='x', field_name='x')
        with self.assertRaises(ValueError):
            # each choice must be a 3-tuple
            ChoiceFilter(choices=[('a', 'a', 'a'), ('b', 'b')], display_name='x', field_name='x')

    def test_choice_description(self):
        c = copy(self.test_filters[0])
        c.set_values('1')
        self.assertEqual(c.description(), 'one person')

    def test_get_parms(self):
        c = copy(self.test_filters[0])
        c.set_values('1')
        self.assertEqual({'num': '1'}, c.get_filter_parms())


class AgeFilterTest(FiltersTest):
    def setUp(self):
        self.age_filter = AgeFilter()

    def test_age_filter_constructor_validation(self):
        # It takes no parms
        with self.assertRaises(TypeError):
            AgeFilter('foo')

    def test_age_description(self):
        self.age_filter.set_values([10, 20])
        self.assertEqual(self.age_filter.description(), 'have age between 10 and 20')

    def test_values_validation(self):
        with self.assertRaises(ValueError):
            self.age_filter.set_values(10)
        with self.assertRaises(ValueError):
            self.age_filter.set_values('10')
        with self.assertRaises(ValueError):
            self.age_filter.set_values([])
        with self.assertRaises(ValueError):
            self.age_filter.set_values([10])
        with self.assertRaises(ValueError):
            self.age_filter.set_values([10, 20, 30])
        self.age_filter.set_values(['10', '20'])
        self.assertEqual(self.age_filter.values, [10, 20])
        self.age_filter.set_values([10, 20])
        self.assertEqual(self.age_filter.values, [10, 20])
        self.age_filter.set_values([20, 10])
        self.assertEqual(self.age_filter.values, [10, 20])

    def test_get_parms(self):
        self.age_filter.set_values(['18', '27'])
        self.assertEqual(
            {
                'age__gte': 18,
                'age__lte': 27
            },
            self.age_filter.get_filter_parms()
        )


class FiltersFromRequestTest(FiltersTest):
    def test_no_querystring(self):
        mock_request = MagicMock(GET=QueryDict())
        applied, parms = filters_from_request(self.test_filters, mock_request)
        self.assertEqual(applied, OrderedDict())
        self.assertEqual({}, parms)

    def test_with_choice(self):
        mock_request = MagicMock(GET=QueryDict('num=2'))
        applied, parms = filters_from_request(self.test_filters, mock_request)
        self.assertEqual(len(applied), 1)
        self.assertIn('num', applied)
        self.assertEqual({'num': '2'}, parms)

    def test_with_age(self):
        mock_request = MagicMock(GET=QueryDict('age=2&age=10'))
        applied, parms = filters_from_request(self.test_filters, mock_request)
        self.assertEqual(len(applied), 1)
        self.assertIn('age', applied)
        self.assertEqual({'age__gte': 2, 'age__lte': 10}, parms)

    def test_choice_and_age(self):
        mock_request = MagicMock(GET=QueryDict('age=2&age=10&num=1'))
        applied, parms = filters_from_request(self.test_filters, mock_request)
        self.assertEqual(len(applied), 2)
        self.assertIn('age', applied)
        self.assertIn('num', applied)
        self.assertEqual({'age__gte': 2, 'age__lte': 10, 'num': '1'}, parms)

    def test_two_choices(self):
        mock_request = MagicMock(GET=QueryDict('indent=S&num=1'))
        applied, parms = filters_from_request(self.test_filters, mock_request)
        self.assertEqual(len(applied), 2)
        self.assertIn('indent', applied)
        self.assertIn('num', applied)
        self.assertEqual({'indent': 'S', 'num': '1'}, parms)
