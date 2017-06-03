import datetime

from django.test import TestCase

from voter.models import FileTracker, ChangeTracker, NCVHis, NCVoter
from voter.management.commands.voter_process import process_files, get_file_lines, diff_dicts

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
     "updates_processed": False},
    {"id": 5,
     "etag": "ab476ee500a0421dfab629e8dc464f2a-61",
     "filename": "voter/test_data/ncvoter_3.txt",
     "data_file_kind": "NCVoter",
     "created": datetime.datetime(2017, 5, 2, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
     "change_tracker_processed": False,
     "updates_processed": False},
    {"id": 6,
     "etag": "6dacd80ba773b1295103e268a753f47e-61",
     "filename": "voter/test_data/ncvhis_3.txt",
     "data_file_kind": "NCVHis",
     "created": datetime.datetime(2017, 5, 2, 1, 51, 18, 154276, tzinfo=datetime.timezone.utc),
     "change_tracker_processed": False,
     "updates_processed": False},
    ]


def create_file_trackers():
    return [
        FileTracker.objects.create(**datum)
        for datum in file_trackers_data
        ]


def load_sorted_parsed_csv(filename, ModelClass):
    raw_rows = list(get_file_lines(filename))
    if ModelClass == NCVoter:
        sorted_rows = sorted(raw_rows, key=lambda k: k['ncid'])
    if ModelClass == NCVHis:
        sorted_rows = sorted(raw_rows, key=lambda k: (k['ncid'], k['election_desc']))
    return [ModelClass.parse_row(row) for row in sorted_rows]


def query_csv_data_in_model(ModelClass):
    if ModelClass == NCVoter:
        order_by_attrs = ('ncid',)
    else:
        order_by_attrs = ('ncid', 'election_desc')
    query_results = list(ModelClass.objects.order_by(*order_by_attrs).values())
    return [
        {k: v for k, v in row.items() if v != '' and k != 'id' and v != None}
        for row in query_results
    ]


class VoterProcessChangeTrackerTest(TestCase):

    maxDiff = None

    def setUp(self):
        self.file_trackers = create_file_trackers()

    def test_change_tracker_tallies(self):
        change_tallies = process_files(output=False)
        self.assertEquals(change_tallies, [
            {'filename': 'voter/test_data/ncvoter_1.txt', 'file_tracker_id': 1, 'added': 8, 'modified': 0, 'ignored': 0},
            {'filename': 'voter/test_data/ncvoter_2.txt', 'file_tracker_id': 3, 'added': 1, 'modified': 1, 'ignored': 7},
            {'filename': 'voter/test_data/ncvoter_3.txt', 'file_tracker_id': 5, 'added': 0, 'modified': 0, 'ignored': 9}])

    def test_change_tracker_modified_values(self):
        process_files(output=False)
        ncvoter_modifieds = ChangeTracker.objects.filter(
            model_name=FileTracker.DATA_FILE_KIND_NCVOTER, op_code=ChangeTracker.OP_CODE_MODIFY)
        self.assertEquals(ncvoter_modifieds.count(), 1)
        self.assertEquals(ncvoter_modifieds[0].data,
                          {'drivers_lic': False,
                           'mail_addr1': '123 SESAME ST',
                           'res_street_address': '123 SESAME ST'})


class VoterProcessIntegrationTest(TestCase):

    maxDiff = None

    def setUp(self):
        self.file_trackers = create_file_trackers()

    def test_process_changes_integration(self):
        process_files(output=False)
        self.assertEquals(NCVoter.objects.count(), 9)
        latest_ncvoter_file_data = load_sorted_parsed_csv("voter/test_data/ncvoter_2.txt", NCVoter)
        latest_ncvoter_db_data = query_csv_data_in_model(NCVoter)
        self.assertEquals(latest_ncvoter_file_data, latest_ncvoter_db_data)
