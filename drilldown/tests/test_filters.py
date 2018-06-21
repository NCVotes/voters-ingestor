from collections import OrderedDict
from copy import copy
from unittest.mock import MagicMock, patch

from django.http import QueryDict
from django.test import TestCase

from drilldown.filters import ChoiceFilter, MultiChoiceFilter, AgeFilter, FreeTextFilter, filters_from_request


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
            MultiChoiceFilter(
                choices=[
                    ('C', 'cats', 'who like cats'),
                    ('D', 'dogs', 'who like dogs'),
                ],
                display_name="Pet preferences",
                field_name="pet",

            ),
            AgeFilter(),
            FreeTextFilter(
                display_name='Random anything',
                field_name='rando',
                prefix='go to the',
            ),
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

    def test_get_params(self):
        c = copy(self.test_filters[0])
        c.set_values('1')
        self.assertEqual({'num': '1'}, c.get_filter_params())

    def test_render(self):
        c = copy(self.test_filters[0])
        c.set_values('1')
        self.assertHTMLEqual(c.render_values(), "<input name='num' type='hidden' value='1' />")


class MultiChoiceFilterTest(FiltersTest):
    def setUp(self):
        self.c = copy(self.test_filters[2])

    def test_get_params(self):
        "params get converted to an __in query"
        self.c.set_values(['C', 'D'])
        self.assertEqual({'pet__in': ['C', 'D']}, self.c.get_filter_params())

    def test_get_label(self):
        self.assertEqual(self.c.get_label('C'), 'cats')

    def test_choice_description(self):
        self.c.set_values(['C'])
        self.assertEqual(self.c.description(), 'have Pet preferences of <em>cats</em>')
        self.c.set_values(['C', 'D'])
        self.assertEqual(self.c.description(), 'have Pet preferences of <em>cats or dogs</em>')


class AgeFilterTest(FiltersTest):
    def setUp(self):
        self.age_filter = AgeFilter()

    def test_age_filter_constructor_validation(self):
        # It takes no params
        with self.assertRaises(TypeError):
            AgeFilter('foo')

    def test_age_description(self):
        self.age_filter.set_values([10, 20])
        self.assertEqual(self.age_filter.description(), 'have age between 10 and 20')
        self.age_filter.set_values([None, 20])
        self.assertEqual(self.age_filter.description(), 'have age less than or equal to 20')
        self.age_filter.set_values([10, None])
        self.assertEqual(self.age_filter.description(), 'have age greater than or equal to 10')

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
        self.age_filter.set_values([None, None])
        self.assertEqual(self.age_filter.errors, ['Must enter min age, max age, or both.'])
        self.age_filter.set_values(['10', '20'])
        self.assertEqual(self.age_filter.values, [10, 20])
        self.age_filter.set_values([10, 20])
        self.assertEqual(self.age_filter.values, [10, 20])
        self.age_filter.set_values([20, 10])
        self.assertEqual(self.age_filter.values, [10, 20])

    def test_get_params(self):
        self.age_filter.set_values(['18', '27'])
        self.assertEqual(
            {
                'age__gte': 18,
                'age__lte': 27
            },
            self.age_filter.get_filter_params()
        )


class FreeTextFilterTest(FiltersTest):
    def setUp(self):
        self.free = copy(self.test_filters[4])

    def test_it(self):
        self.free.set_values(['dance party'])
        self.assertEqual(self.free.description(), 'go to the dance party')
        self.assertEqual(self.free.get_filter_params(), {'rando': 'dance party'})


@patch('drilldown.filters.NCVoter')
class FiltersFromRequestTest(FiltersTest):
    def test_no_querystring(self, mock_ncvoter):
        mock_request = MagicMock(GET=QueryDict())
        applied, params = filters_from_request(self.test_filters, mock_request)
        self.assertEqual(applied, OrderedDict())
        self.assertEqual({}, params)

    def test_with_choice(self, mock_ncvoter):
        mock_request = MagicMock(GET=QueryDict('num=2'))
        applied, params = filters_from_request(self.test_filters, mock_request)
        self.assertEqual(len(applied), 1)
        self.assertIn('num', applied)
        self.assertEqual({'num': '2'}, params)

    def test_with_age(self, mock_ncvoter):
        mock_request = MagicMock(GET=QueryDict('age=2&age=10'))
        applied, params = filters_from_request(self.test_filters, mock_request)
        self.assertEqual(len(applied), 1)
        self.assertIn('age', applied)
        self.assertEqual({'age__gte': 2, 'age__lte': 10}, params)

    def test_choice_and_age(self, mock_ncvoter):
        mock_request = MagicMock(GET=QueryDict('age=2&age=10&num=1'))
        applied, params = filters_from_request(self.test_filters, mock_request)
        self.assertEqual(len(applied), 2)
        self.assertIn('age', applied)
        self.assertIn('num', applied)
        self.assertEqual({'age__gte': 2, 'age__lte': 10, 'num': '1'}, params)

    def test_two_choices(self, mock_ncvoter):
        mock_request = MagicMock(GET=QueryDict('indent=S&num=1'))
        applied, params = filters_from_request(self.test_filters, mock_request)
        self.assertEqual(len(applied), 2)
        self.assertIn('indent', applied)
        self.assertIn('num', applied)
        self.assertEqual({'indent': 'S', 'num': '1'}, params)

    def test_free_text(self, mock_ncvoter):
        mock_request = MagicMock(GET=QueryDict('rando=quincieñera'))
        applied, params = filters_from_request(self.test_filters, mock_request)
        self.assertEqual(len(applied), 1)
        self.assertIn('rando', applied)
        self.assertEqual({'rando': 'quincieñera'}, params)

    @patch('drilldown.filters.logger.warning')
    def test_with_nonexistent_choice(self, mock_warning, mock_ncvoter):
        mock_request = MagicMock(GET=QueryDict('foo=2'))
        applied, params = filters_from_request(self.test_filters, mock_request)
        # no filters applied, and a warning is issued
        self.assertEqual(len(applied), 0)
        self.assertEqual(params, {})
        mock_warning.assert_called()
