from unittest.mock import Mock, patch

from django.http import QueryDict
from django.test import TestCase

from voter.models import NCVoter
from matview.models import MatView
from .templatetags import query_string as qs_tags
from . import views


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
        filter_list = []
        filters = {}
        views.add_filter(filter_list, filters, "foo", "bar")

        assert filters['foo'] == 'bar'
        assert len(filter_list) == 1

        assert filter_list[0]['description'] == 'foo=bar'
        assert filter_list[0]['count'] == 0

    def test_add_filter_nice(self):
        views.FILTERS["some_field"] = {}
        views.FILTERS["some_field"]["some_value"] = {
            "label": "Something",
            "description": "Who match some criteria",
        }

        filter_list = []
        filters = {}
        views.add_filter(filter_list, filters, "some_field", "some_value")

        assert filter_list[0]['description'] == "Who match some criteria"

    def test_add_filters_count(self):
        NCVoter.objects.create(ncid='A1', data={"party_cd": "DEM"})
        MatView.refresh_all()

        filter_list = []
        filters = {}
        views.add_filter(filter_list, filters, "party_cd", "DEM")

        assert filter_list[0]['count'] == 1

    def test_drilldown_view(self):
        with patch("drilldown.views.add_filter") as add_filter:
            request = Mock()
            request.GET = QueryDict('party_cd=DEM')
            views.drilldown(request)

            add_filter.assert_called_once_with([], {}, "party_cd", "DEM")
