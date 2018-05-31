import time

from django.test import TestCase

from voter.models import NCVoter
from matview.models import MatView
from . import models


class RegisterTestCase(TestCase):

    def test_register_empty(self):
        models.register_query("foo.Bar", {})
        assert 'foo' in models.queries
        assert 'Bar' in models.queries['foo']
        assert ['matview_mv_foo_bar__count'] == list(models.queries['foo']['Bar'])

    def test_register_nonempty(self):
        models.register_query("foo.Bar", {"x": "y"})
        assert 'foo' in models.queries
        assert 'Bar' in models.queries['foo']
        assert 'matview_mv_foo_bar_x_y__count' in models.queries['foo']['Bar']
        assert 'matview_mv_foo_bar_x_y' in models.queries['foo']['Bar']


class CountTestCase(TestCase):

    def setUp(self):
        ncid = 1
        for party in ('DEM', 'REP'):
            for sexcode in ('M', 'F'):
                data = {
                    "party_cd": party,
                    "gender_code": sexcode,
                }
                NCVoter.objects.create(ncid=str(ncid), data=data)
                ncid += 1

        MatView.refresh_all()

    def test_count_all(self):
        self.assertEqual(4, models.get_count("voter.NCVoter", {}))

    def test_count_dems(self):
        self.assertEqual(2, models.get_count("voter.NCVoter", {"party_cd": "DEM"}))

    def test_count_males(self):
        self.assertEqual(2, models.get_count("voter.NCVoter", {"gender_code": "M"}))

    def test_count_rep_females(self):
        self.assertEqual(1, models.get_count("voter.NCVoter", {"party_cd": "REP", "gender_code": "F"}))


class QueryTestCase(TestCase):

    def setUp(self):
        ncid = 1
        for ncid, party, gender, first, last in (
            ("A1", "DEM", "F", "Mary", "Lambert"),
            ("A2", "DEM", "M", "Harry", "Lambert"),
            ("A3", "DEM", "F", "Daria", "Smith"),
            ("A4", "REP", "M", "Timothy", "Bolton"),
            ("A5", "REP", "F", "Sarah", "Littleton"),
        ):
            NCVoter.objects.create(
                ncid=ncid, data={
                    "party_cd": party,
                    "gender_code": gender,
                    "first_name": first,
                    "last_name": last,
                }
            )

        MatView.refresh_all()

    def assertIsSubset(self, left, right):
        left = set(left)
        right = set(right)
        extra_left = left - right

        if extra_left:
            raise AssertionError(
                "First set is not a subset of second. Values not in second set: %s"
                % ', '.join(str(v) for v in extra_left))

    def test_all_fallback(self):
        assert 5 == models.get_query("voter.NCVoter", {}).count()

        NCVoter.objects.all().delete()
        assert 0 == models.get_query("voter.NCVoter", {}).count()

    def test_single_key(self):
        # So we know we're querying the materialized views
        NCVoter.objects.all().delete()

        q = models.get_query("voter.NCVoter", {"party_cd": "REP"})
        ncids = q.values_list('ncid', flat=True)
        self.assertIsSubset(("A4", "A5"), ncids)

    def test_multi_key(self):
        # So we know we're querying the materialized views
        NCVoter.objects.all().delete()

        q = models.get_query("voter.NCVoter", {"party_cd": "DEM", "gender_code": "F"})
        ncids = q.values_list('ncid', flat=True)
        self.assertIsSubset(("A1", "A3"), ncids)

    def test_deep_filtering(self):
        # So we know we're querying the materialized views
        NCVoter.objects.all().delete()

        q = models.get_query("voter.NCVoter", {"party_cd": "DEM", "last_name": "Lambert"})
        ncids = q.values_list('ncid', flat=True)
        self.assertIsSubset(("A1", "A2"), ncids)
