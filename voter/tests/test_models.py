from unittest.mock import patch

from django.test import TestCase

from voter.models import FileTracker, BadLineTracker, BadLineRange, NCVoter, NCVoterQueryView
from voter.tests import factories


class FileTrackerTest(TestCase):

    def test_short_filename_for_path_is_correct(self):
        f = FileTracker(filename='/foo/bar.txt')
        self.assertEqual(f.short_filename, 'bar.txt')

    def test_short_filename_if_no_parent(self):
        f = FileTracker(filename='bar.txt')
        self.assertEqual(f.short_filename, 'bar.txt')


class BadLineTrackerTest(TestCase):
    def setUp(self):
        self.blr = BadLineTracker('filename')

    def test_just_one_error(self):
        self.blr.error(27, 'bad line', 'the line was bad')
        self.blr.flush()
        self.assertEqual(1, BadLineRange.objects.count())
        r = BadLineRange.objects.first()
        self.assertEqual(27, r.first_line_no)
        self.assertEqual(27, r.last_line_no)
        self.assertEqual('bad line', r.example_line)
        self.assertEqual('the line was bad', r.message)
        self.assertEqual('filename', r.filename)
        self.assertFalse(r.is_warning)

    def test_adjacent_errors(self):
        self.blr.error(27, 'bad line', 'the line was bad')
        self.blr.error(28, 'worse line', 'the line was bad')
        self.blr.flush()
        self.assertEqual(1, BadLineRange.objects.count())
        r = BadLineRange.objects.first()
        self.assertEqual(27, r.first_line_no)
        self.assertEqual(28, r.last_line_no)
        self.assertEqual('bad line', r.example_line)
        self.assertEqual('the line was bad', r.message)
        self.assertEqual('filename', r.filename)
        self.assertFalse(r.is_warning)

    def test_gap_in_errors(self):
        self.blr.error(27, 'bad line', 'the line was bad')
        self.blr.error(29, 'worse line', 'the line was bad')
        self.blr.flush()
        self.assertEqual(2, BadLineRange.objects.count())
        r = BadLineRange.objects.order_by('first_line_no').first()
        self.assertEqual(27, r.first_line_no)
        self.assertEqual(27, r.last_line_no)
        self.assertEqual('bad line', r.example_line)
        self.assertEqual('the line was bad', r.message)
        self.assertEqual('filename', r.filename)
        self.assertFalse(r.is_warning)
        r = BadLineRange.objects.order_by('-first_line_no').first()
        self.assertEqual(29, r.first_line_no)
        self.assertEqual(29, r.last_line_no)
        self.assertEqual('worse line', r.example_line)
        self.assertEqual('the line was bad', r.message)
        self.assertEqual('filename', r.filename)
        self.assertFalse(r.is_warning)

    def test_different_messages(self):
        self.blr.error(27, 'bad line', 'the line was bad')
        self.blr.error(28, 'worse line', 'the line was worse')
        self.blr.flush()
        self.assertEqual(2, BadLineRange.objects.count())
        r = BadLineRange.objects.order_by('first_line_no').first()
        self.assertEqual(27, r.first_line_no)
        self.assertEqual(27, r.last_line_no)
        self.assertEqual('bad line', r.example_line)
        self.assertEqual('the line was bad', r.message)
        self.assertEqual('filename', r.filename)
        self.assertFalse(r.is_warning)
        r = BadLineRange.objects.order_by('-first_line_no').first()
        self.assertEqual(28, r.first_line_no)
        self.assertEqual(28, r.last_line_no)
        self.assertEqual('worse line', r.example_line)
        self.assertEqual('the line was worse', r.message)
        self.assertEqual('filename', r.filename)
        self.assertFalse(r.is_warning)

    def test_warning_error(self):
        self.blr.warning(27, 'bad line', 'the line was bad')
        self.blr.error(28, 'worse line', 'the line was bad')
        self.blr.flush()
        self.assertEqual(2, BadLineRange.objects.count())
        r = BadLineRange.objects.order_by('first_line_no').first()
        self.assertEqual(27, r.first_line_no)
        self.assertEqual(27, r.last_line_no)
        self.assertEqual('bad line', r.example_line)
        self.assertEqual('the line was bad', r.message)
        self.assertEqual('filename', r.filename)
        self.assertTrue(r.is_warning)
        r = BadLineRange.objects.order_by('-first_line_no').first()
        self.assertEqual(28, r.first_line_no)
        self.assertEqual(28, r.last_line_no)
        self.assertEqual('worse line', r.example_line)
        self.assertEqual('the line was bad', r.message)
        self.assertEqual('filename', r.filename)
        self.assertFalse(r.is_warning)


class NCVoterTest(TestCase):

    def test_get_count_uses_materialized_view(self):
        factories.NCVoter()
        # materialized query view is not refreshed, so will get zero records
        self.assertEqual(NCVoter.get_count({}), 0)
        NCVoterQueryView.refresh()
        self.assertEqual(NCVoter.get_count({}), 1)

    def test_get_count_is_cached_in_db(self):
        factories.NCVoterQueryCache(qs_filters={}, count=23)
        with patch('voter.models.NCVoterQueryView.objects.filter') as mock_queryview:
            self.assertEqual(NCVoter.get_count({}), 23)
        mock_queryview.assert_not_called()
