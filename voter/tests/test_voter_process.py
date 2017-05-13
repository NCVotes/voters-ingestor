import datetime

from django.test import TestCase

from voter.models import FileTracker, ChangeTracker, NCVHis, NCVoter
from voter.management.commands.voter_process import process_files


file_trackers_data = [
    {"id": 1,
     "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
     "filename": "voter/test_data/ncvoter_1.txt",
     "data_file_kind": "NCVoter",
     "created": datetime.datetime(2017, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
     "change_tracker_processed": False,
     "updates_processed": False},
    {"id": 2,
     "etag": "6dacd80ba773b1295103e268a753f47e-35",
     "filename": "voter/test_data/ncvhis_1.txt",
     "data_file_kind": "NCVHis",
     "created": datetime.datetime(2017, 4, 30, 1, 51, 18, 154276, tzinfo=datetime.timezone.utc),
     "change_tracker_processed": False,
     "updates_processed": False},
    {"id": 3,
     "etag": "ab476ee500a0421dfab629e8dc464f2a-60",
     "filename": "voter/test_data/ncvoter_2.txt",
     "data_file_kind": "NCVoter",
     "created": datetime.datetime(2017, 5, 1, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
     "change_tracker_processed": False,
     "updates_processed": False},
    {"id": 4,
     "etag": "6dacd80ba773b1295103e268a753f47e-60",
     "filename": "voter/test_data/ncvhis_2.txt",
     "data_file_kind": "NCVHis",
     "created": datetime.datetime(2017, 5, 1, 1, 51, 18, 154276, tzinfo=datetime.timezone.utc),
     "change_tracker_processed": False,
     "updates_processed": False},]


def create_file_trackers():
    return [
        FileTracker.objects.create(**datum)
        for datum in file_trackers_data
        ]


class Simple(TestCase):

    def setUp(self):
        self.file_trackers = create_file_trackers()

    def test_change_tracker_tallies(self):
        change_tallies = process_files(create_changes_only=True)
        self.assertEquals(change_tallies,
                          [[{'filename': "voter/test_data/ncvhis_1.txt",
                             'file_tracker_id': 2,
                             'added': 8, 'ignored': 0, 'modified': 0},
                            {'filename': "voter/test_data/ncvhis_2.txt",
                             'file_tracker_id': 4,
                             'added': 1, 'ignored': 7, 'modified': 1}],
                           [{'filename': "voter/test_data/ncvoter_1.txt",
                             'file_tracker_id': 1,
                             'added': 8, 'ignored': 0, 'modified': 0},
                            {'filename': "voter/test_data/ncvoter_2.txt",
                             'file_tracker_id': 3,
                             'added': 1, 'ignored': 7, 'modified': 1}]])
