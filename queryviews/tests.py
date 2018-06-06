from unittest.mock import patch
from django.test import TestCase

from voter.models import NCVoter
from matview.models import MatView
from drilldown.filters import RaceFilter

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


class FlagTests(TestCase):
    def setUp(self):
        ncid = 1
        for rc, rl, rd in RaceFilter.RACES:
            for party in ('DEM', 'REP'):
                data = {
                    "party_cd": party,
                    "race_code": rc,
                }
                NCVoter.objects.create(ncid=str(ncid), data=data)
                ncid += 1

        MatView.refresh_all()

    def test_flags_exist(self):
        assert NCVoter.objects.filter(data__race_code='W').first().data['raceflag_w'] == 'true'
        assert NCVoter.objects.filter(data__race_code='W').first().data['raceflag_bw'] == 'true'
        assert NCVoter.objects.filter(data__race_code='W').first().data['raceflag_biw'] == 'true'
        assert 'raceflag_b' not in NCVoter.objects.filter(data__race_code='W').first().data
        assert 'raceflag_wb' not in NCVoter.objects.filter(data__race_code='W').first().data

    def test_count_single_code(self):
        assert 2 == models.get_count("voter.NCVoter", {"race_code": "B"})

    def test_count_single_code_w_filter(self):
        assert 1 == models.get_count("voter.NCVoter", {"race_code": "B", "party_cd": "REP"})

    def test_count_two_code(self):
        assert 4 == models.get_count("voter.NCVoter", {"race_code": ["B", "A"]})

    def test_count_two_code_w_filter(self):
        assert 2 == models.get_count("voter.NCVoter", {"race_code": ["B", "A"], "party_cd": "DEM"})

    def test_count_aggregate(self):
        assert 6 == models.get_count("voter.NCVoter", {"race_code": ["B", "A", "I"]})

    def test_count_aggregate_w_filter(self):
        assert 3 == models.get_count("voter.NCVoter", {"race_code": ["B", "A", "I"], "party_cd": "REP"})

    def test_sample_single_code(self):
        i = iter(range(100))
        with patch("random.randint", lambda s, e: next(i)):
            sample = models.get_random_sample(1, "voter.NCVoter", {"race_code": "B"})
            assert len(sample) == 1
            assert sample[0].ncid == NCVoter.objects.filter(data__race_code="B").values_list('ncid', flat=True)[0]

            sample = models.get_random_sample(1, "voter.NCVoter", {"race_code": "B"})
            assert len(sample) == 1
            assert sample[0].ncid == NCVoter.objects.filter(data__race_code="B").values_list('ncid', flat=True)[1]

    def test_sample_pair(self):
        get_query_orig = models.get_query
        i = iter(range(100))
        with patch("queryviews.models.random") as random:
            with patch("queryviews.models.get_query") as get_query_mock:
                random.randint = lambda s, e: next(i)
                random.shuffle = lambda x: None
                get_query_mock.side_effect = lambda *a, **kw: sorted(get_query_orig(*a, **kw), key=lambda v: v.id)

                ncid_set = set(NCVoter.objects.filter(data__race_code__in=["B", "A"]).values_list('ncid', flat=True))
                assert len(ncid_set) == 4

                sample = models.get_random_sample(2, "voter.NCVoter", {"race_code": "BA"})
                assert len(sample) == 2
                ncid_set.discard(sample[0].ncid)
                ncid_set.discard(sample[1].ncid)
                assert len(ncid_set) == 2

    def test_cross_aggregate(self):
        """This will combine 3 separate flag queries, w/ 1 results each, into one set of results to sample from."""

        not_w = ['O', 'B', 'M', 'I', 'U', 'A']
        ncid_set = set(NCVoter.objects.filter(data__race_code__in=not_w).values_list('ncid', flat=True))
        assert len(ncid_set) == 12

        rand_seq = iter(range(100))
        with patch("random.randint", lambda s, e: next(rand_seq)):
            # This will combine a random result from each of the three sub-queries
            sample = models.get_random_sample(3, "voter.NCVoter", {"race_code": not_w})
            assert len(sample) == 3
            ncid_set.discard(sample[0].ncid)
            ncid_set.discard(sample[1].ncid)
            ncid_set.discard(sample[2].ncid)
            assert len(ncid_set) == 9

    def test_cross_aggregate_uneven(self):
        """This will combine 3 separate flag queries, but the number of requested results won't divide evenly."""

        not_w = ['O', 'B', 'M', 'I', 'U', 'A']
        ncid_set = set(NCVoter.objects.filter(data__race_code__in=not_w).values_list('ncid', flat=True))
        assert len(ncid_set) == 12

        rand_seq = iter(range(100))
        with patch("random.randint", lambda s, e: next(rand_seq)):
            # This will combine a random result from each of the three sub-queries
            # but, an extra result from one of them randomly to make the 4th
            sample = models.get_random_sample(4, "voter.NCVoter", {"race_code": not_w})
            assert len(sample) == 4
            ncid_set.discard(sample[0].ncid)
            ncid_set.discard(sample[1].ncid)
            ncid_set.discard(sample[2].ncid)
            ncid_set.discard(sample[3].ncid)
            assert len(ncid_set) == 8
