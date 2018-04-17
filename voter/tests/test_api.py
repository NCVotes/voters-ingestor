from datetime import datetime
from unittest.mock import Mock, patch

from django.test import TestCase

from voter import models
from voter.views import changes


class APIChangesTests(TestCase):

    def make_request(self, params):
        request = Mock()
        request.GET = params
        return request

    def make_change(self, ncid, data):
        now = datetime.now()
        ft = models.FileTracker.objects.get_or_create(filename="data.txt", defaults={'created': now})[0]
        voter = models.NCVoter.objects.get_or_create(ncid=ncid)[0]
        lineno = models.ChangeTracker.objects.filter(file_tracker=ft).count()
        op_code = 'A' if voter.changelog.count() == 0 else 'M'

        models.ChangeTracker.objects.create(
            file_tracker=ft,
            file_lineno=lineno,
            snapshot_dt=now,
            op_code=op_code,
            voter=voter,
            data=data,
        )

    def test_changed_required(self):
        resp = changes(self.make_request({}))
        assert resp.status_code == 400

    def test_no_added_records(self):
        self.make_change("A1", {
            'last_name': 'SMITH',
        })

        with patch("voter.views.JsonResponse") as jr:
            jr.side_effect = lambda x, *a, **kw: x
            resp = changes(self.make_request({'changed': 'last_name'}))

        assert set(('_elapsed',)) == set(resp.keys())

    def test_finds_changes_only(self):
        self.make_change("A1", {
            'last_name': 'SMITH',
        })
        self.make_change("A1", {
            'last_name': 'WILLIAMS',
        })

        self.make_change("A2", {
            'last_name': 'WEST',
        })
        self.make_change("A2", {
            # Because the field excluded if it didn't change at import time
        })

        with patch("voter.views.JsonResponse") as jr:
            jr.side_effect = lambda x, *a, **kw: x
            resp = changes(self.make_request({'changed': 'last_name'}))

        assert resp['A1']['new'] == 'WILLIAMS'
        assert resp['A1']['old'] == 'SMITH'
        assert 'A2' not in resp

    def test_specific_changes_only(self):
        self.make_change("A1", {
            'last_name': 'SMITH',
        })
        self.make_change("A1", {
            'last_name': 'WILLIAMS',
        })

        self.make_change("A2", {
            'last_name': 'WEST',
        })
        self.make_change("A2", {
            'last_name': 'EAST',
        })

        with patch("voter.views.JsonResponse") as jr:
            jr.side_effect = lambda x, *a, **kw: x
            resp = changes(self.make_request({'changed': 'last_name', 'new': 'EAST'}))

        assert resp['A2']['new'] == 'EAST'
        assert resp['A2']['old'] == 'WEST'
        assert 'A1' not in resp

    def test_limit(self):
        for i in range(1, 11):
            self.make_change("A%s" % i, {
                'last_name': 'SMITH',
            })
            self.make_change("A%s" % i, {
                'last_name': 'WILLIAMS',
            })

        with patch("voter.views.JsonResponse") as jr:
            jr.side_effect = lambda x, *a, **kw: x
            resp = changes(self.make_request({'changed': 'last_name', 'limit': '5'}))

        assert 6 == len(resp)  # 5 NCIDs + _elapsed key
