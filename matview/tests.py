from django.db import connection
from django.test import TestCase

from voter.models import NCVoter
from . import dbutils


class MatViewNameTests(TestCase):

    def test_empty(self):
        name = dbutils.get_matview_name("foo.Bar", {})
        self.assertEqual(name, "matview_mv_foo_bar")

    def test_basic_name(self):
        name = dbutils.get_matview_name("foo.Bar", {"x": "y"})
        self.assertEqual(name, "matview_mv_foo_bar_x_y")

    def test_names_are_ordered(self):
        name = dbutils.get_matview_name("foo.Bar", {"x": "y", "a": "b"})
        self.assertEqual(name, "matview_mv_foo_bar_a_b_xx_x_y")


class MatViewMigrationTest(TestCase):

    def setUp(self):
        NCVoter.objects.create(ncid='A1', data={"party_cd": "REP"})
        NCVoter.objects.create(ncid='A2', data={"party_cd": "DEM"})
        self.migration = dbutils._make_matview_migration("voter_ncvoter", {"party_cd": "DEM"}, "matview_mv_test")
        with connection.cursor() as cursor:
            cursor.execute(self.migration.sql)

    def tearDown(self):
        with connection.cursor() as cursor:
            cursor.execute(self.migration.reverse_sql)

    def test_materialized_data(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM matview_mv_test;")
            row = cursor.fetchone()
        self.assertEqual('A2', row[1])

    def test_materialized_count(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM matview_mv_test__count;")
            row = cursor.fetchone()
        self.assertEqual(1, row[1])
