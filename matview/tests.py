from django.db import connection
from django.test import TestCase

from voter.models import NCVoter
from .models import partition
from . import dbutils


class UtilTests(TestCase):

    def test_partition_evenly(self):
        numbers = list(range(1, 17))
        groups = partition(numbers, 4)
        self.assertEqual(groups[0], [1, 2, 3, 4])
        self.assertEqual(groups[1], [5, 6, 7, 8])
        self.assertEqual(groups[2], [9, 10, 11, 12])
        self.assertEqual(groups[3], [13, 14, 15, 16])

    def test_partition_short(self):
        numbers = list(range(1, 16))
        groups = partition(numbers, 4)
        lengths = [len(group) for group in groups]
        self.assertEqual(4, len(groups))
        self.assertEqual(1, lengths.count(3))
        self.assertEqual(3, lengths.count(4))
    
    def test_partition_long(self):
        numbers = list(range(1, 18))
        groups = partition(numbers, 4)
        lengths = [len(group) for group in groups]
        self.assertEqual(4, len(groups))
        self.assertEqual(1, lengths.count(5))
        self.assertEqual(3, lengths.count(4))


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
        self.migration = dbutils._make_matview_sql_migration("voter_ncvoter", {"party_cd": "DEM"}, "matview_mv_test")
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
