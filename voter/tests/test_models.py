from django.test import TestCase

from voter.models import FileTracker


class FileTrackerTest(TestCase):

    def test_short_filename_for_path_is_correct(self):
        f = FileTracker(filename='/foo/bar.txt')
        self.assertEqual(f.short_filename, 'bar.txt')

    def test_short_filename_if_no_parent(self):
        f = FileTracker(filename='bar.txt')
        self.assertEqual(f.short_filename, 'bar.txt')
