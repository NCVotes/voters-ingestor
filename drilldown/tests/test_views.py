from collections import OrderedDict
from unittest.mock import Mock, patch, MagicMock

from django.http import QueryDict
from django.test import TestCase

from drilldown.filters import filters_from_request
from drilldown.templatetags import query_string as qs_tags
from drilldown import views
from drilldown.views import declared_filters


class QueryStringTagsTests(TestCase):

    def test_qs_trim(self):
        request = Mock()
        request.GET = QueryDict('', mutable=True)
        request.GET['x'] = '1'
        request.GET['y'] = '2'
        qs = qs_tags.qs_trim(request, "y")

        self.assertEqual("x=1", qs)


class ViewTests(TestCase):

    def test_add_filter_defaults(self):
        mock_request = MagicMock(GET=QueryDict())
        applied, filters = filters_from_request(declared_filters, mock_request)
        assert len(filters) == 0
        assert len(applied) == 0

    def test_one_filter(self):
        mock_request = MagicMock(GET=QueryDict('county_desc=ORANGE'))
        applied, filters = filters_from_request(declared_filters, mock_request)
        self.assertEqual(filters, {'county_desc': 'ORANGE'})
        self.assertEqual(1, len(applied))
        last_filter = list(applied.values())[-1]
        self.assertEqual(last_filter.filter_params, filters)
        self.assertIn('ORANGE'.title(), last_filter.description())

    def test_two_filters(self):
        mock_request = MagicMock(GET=QueryDict('county_desc=ORANGE&gender_code=F'))
        applied, filters = filters_from_request(declared_filters, mock_request)
        self.assertEqual(filters, {'county_desc': 'ORANGE', 'gender_code': 'F'})
        self.assertEqual(2, len(applied))
        last_filter = list(applied.values())[-1]
        self.assertEqual(last_filter.filter_params, filters)
        self.assertIn('female', last_filter.description())

    def test_drilldown_view(self):
        with patch('drilldown.views.filters_from_request') as mock_from_request:
            request = MagicMock(GET=QueryDict('party_cd=DEM'))
            mock_from_request.return_value = [OrderedDict(), {}]
            views.drilldown(request)

            mock_from_request.assert_called_once_with(declared_filters, request)
