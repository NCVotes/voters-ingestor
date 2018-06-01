from collections import OrderedDict
from copy import copy
from unittest.mock import MagicMock

from django.http import QueryDict
from django.test import TestCase

from drilldown.filters import ChoiceFilter, filters_from_request


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

            )
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

    def test_two_choices(self):
        mock_request = MagicMock(GET=QueryDict('indent=S&num=1'))
        applied, parms = filters_from_request(self.test_filters, mock_request)
        self.assertEqual(len(applied), 2)
        self.assertIn('indent', applied)
        self.assertIn('num', applied)
        self.assertEqual({'indent': 'S', 'num': '1'}, parms)
