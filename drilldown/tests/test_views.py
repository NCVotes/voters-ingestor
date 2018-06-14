from collections import OrderedDict
from unittest.mock import patch, MagicMock

from django.http import QueryDict
from django.test import TestCase

from drilldown.filters import filters_from_request
from drilldown import views
from drilldown.views import declared_filters


class DrilldownViewTests(TestCase):

    def test_add_filter_defaults(self):
        mock_request = MagicMock(GET=QueryDict())
        applied, filters = filters_from_request(declared_filters, mock_request)
        assert len(filters) == 0
        assert len(applied) == 0

    def test_one_filter(self):
        mock_request = MagicMock(GET=QueryDict('county_id=68'))
        applied, filters = filters_from_request(declared_filters, mock_request)
        self.assertEqual(filters, {'county_id': '68'})
        self.assertEqual(1, len(applied))
        last_filter = list(applied.values())[-1]
        self.assertEqual(last_filter.filter_params, filters)
        self.assertIn('ORANGE'.title(), last_filter.description())

    def test_two_filters(self):
        mock_request = MagicMock(GET=QueryDict('county_id=68&gender_code=F'))
        applied, filters = filters_from_request(declared_filters, mock_request)
        self.assertEqual(filters, {'county_id': '68', 'gender_code': 'F'})
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


class SampleViewTests(TestCase):

    def test_sample_view(self):
        with patch('drilldown.views.filters_from_request') as mock_from_request:
            request = MagicMock(GET=QueryDict('party_cd=DEM'))
            mock_from_request.return_value = [OrderedDict(), {}]
            views.sample(request)

            mock_from_request.assert_called_once_with(declared_filters, request)
