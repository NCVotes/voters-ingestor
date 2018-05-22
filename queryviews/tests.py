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


class QueryTestCase(TestCase):

    def setUp(self):
        ncid = 1
        for party in ('DEM', 'REP'):
            for sexcode in ('M', 'F'):
                data = {
                    "party_cd": party,
                    "sex_code": sexcode,
                }
                NCVoter.objects.create(ncid=str(ncid), data=data)
                ncid += 1

        MatView.refresh_all()

    def test_count_all(self):
        self.assertEqual(4, models.get_count("voter.NCVoter", {}))

    def test_count_dems(self):
        self.assertEqual(2, models.get_count("voter.NCVoter", {"party_cd": "DEM"}))

    def test_count_males(self):
        self.assertEqual(2, models.get_count("voter.NCVoter", {"sex_code": "M"}))

    def test_count_rep_females(self):
        self.assertEqual(1, models.get_count("voter.NCVoter", {"party_cd": "REP", "sex_code": "F"}))
