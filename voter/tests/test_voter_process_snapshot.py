import datetime

from django.test import TestCase

from voter.models import FileTracker, BadLine, ChangeTracker, NCVHis, NCVoter
from voter.management.commands.voter_process_snapshot import process_files, get_file_lines

file_trackers_data = [
    {
        "id": 1,
        "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
        "filename": "voter/test_data/2010-10-31T00-00-00/snapshot_latin1.txt",
        "data_file_kind": "NCVoter",
        "created": datetime.datetime(2011, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
        "change_tracker_processed": False,
    }, {
        "id": 2,
        "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
        "filename": "voter/test_data/2010-10-31T00-00-00/snapshot_utf16.txt",
        "data_file_kind": "NCVoter",
        "created": datetime.datetime(2011, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
        "change_tracker_processed": False,
    }, {
        "id": 3,
        "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
        "filename": "voter/test_data/2011-10-31T00-00-00/snapshot.txt",
        "data_file_kind": "NCVoter",
        "created": datetime.datetime(2012, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
        "change_tracker_processed": False,
    }, {
        "id": 4,
        "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
        "filename": "voter/test_data/2010-10-31T00-00-00/bad_extra45.txt",
        "data_file_kind": "NCVoter",
        "created": datetime.datetime(2011, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
        "change_tracker_processed": False,
    }, {
        "id": 5,
        "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
        "filename": "voter/test_data/2010-10-31T00-00-00/bad_extra45_46_47.txt",
        "data_file_kind": "NCVoter",
        "created": datetime.datetime(2011, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
        "change_tracker_processed": False,
    }, {
        "id": 6,
        "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
        "filename": "voter/test_data/2010-10-31T00-00-00/bad_extra_lots.txt",
        "data_file_kind": "NCVoter",
        "created": datetime.datetime(2011, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
        "change_tracker_processed": False,
    }, {
        "id": 7,
        "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
        "filename": "voter/test_data/2010-10-31T00-00-00/bad_not_enough.txt",
        "data_file_kind": "NCVoter",
        "created": datetime.datetime(2011, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
        "change_tracker_processed": False,
    }
]


def create_file_tracker(i):
    FileTracker.objects.create(**file_trackers_data[i - 1])


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
        {k: v for k, v in row.items() if v != '' and k != 'id' and v is not None}
        for row in query_results
    ]


class VoterProcessChangeTrackerTest(TestCase):

    def tearDown(self):
        FileTracker.objects.all().delete()

    def test_can_consume_latin1(self):
        create_file_tracker(1)
        process_files(output=False)

        # All inserted changes should be additions
        ncvoter_modifieds = ChangeTracker.objects.filter(op_code='A')
        self.assertEquals(ncvoter_modifieds.count(), 19)

        # Can find the first person from the snapshot
        c = ChangeTracker.objects.filter(data__last_name="THOMPSON", data__first_name="JESSICA").first()
        self.assert_(c)

    def test_can_consume_utf16(self):
        create_file_tracker(2)
        process_files(output=False)

        # All inserted changes should be additions
        ncvoter_modifieds = ChangeTracker.objects.filter(op_code='A')
        self.assertEquals(ncvoter_modifieds.count(), 19)

        # Can find the first person from the snapshot
        c = ChangeTracker.objects.filter(data__last_name="BUCKMAN", data__first_name="JOHN").first()
        self.assert_(c)

    def load_two_snapshots(self):
        create_file_tracker(1)
        process_files(output=False)

        create_file_tracker(3)
        process_files(output=False)

    def test_records_modifications(self):
        self.load_two_snapshots()

        additions = ChangeTracker.objects.filter(op_code='A')
        self.assertEquals(additions.count(), 19)

        modifications = ChangeTracker.objects.filter(op_code='M')
        self.assertEquals(modifications.count(), 6)

    def test_records_merge(self):
        self.load_two_snapshots()

        voter = NCVoter.objects.get(ncid="AS2035")
        data = voter.build_current()

        self.assertEqual(data["first_name"], 'VON')
        self.assertEqual(data["last_name"], 'LANGSTON')
    
    def test_extra_data_cell_45(self):
        create_file_tracker(4)
        process_files(output=False)

        self.assertEquals(ChangeTracker.objects.count(), 19)
        self.assertEquals(BadLine.objects.count(), 1)

        badline = BadLine.objects.all().first()
        self.assertEqual(badline.line_no, 19)
        self.assertEqual(badline.filename, "voter/test_data/2010-10-31T00-00-00/bad_extra45.txt")
        self.assertEqual(badline.is_warning, True)
        self.assertIn("(removing 45)", badline.message)

    def test_extra_data_cell_45_46_47(self):
        create_file_tracker(5)
        process_files(output=False)

        self.assertEquals(ChangeTracker.objects.count(), 19)
        self.assertEquals(BadLine.objects.count(), 1)

        badline = BadLine.objects.all().first()
        self.assertEqual(badline.line_no, 19)
        self.assertEqual(badline.filename, "voter/test_data/2010-10-31T00-00-00/bad_extra45_46_47.txt")
        self.assertEqual(badline.is_warning, True)
        self.assertIn("(removing 45-47)", badline.message)

    def test_extra_data_cell_lots(self):
        create_file_tracker(6)
        process_files(output=False)

        # 18, because the bad line was an error and not processed
        self.assertEquals(ChangeTracker.objects.count(), 18)
        self.assertEquals(BadLine.objects.count(), 1)

        badline = BadLine.objects.all().first()
        self.assertEqual(badline.line_no, 19)
        self.assertEqual(badline.filename, "voter/test_data/2010-10-31T00-00-00/bad_extra_lots.txt")
        self.assertEqual(badline.is_warning, False)
        self.assertIn("More cells", badline.message)

    def test_extra_data_cell_lots(self):
        create_file_tracker(7)
        process_files(output=False)

        # 18, because the bad line was an error and not processed
        self.assertEquals(ChangeTracker.objects.count(), 18)
        self.assertEquals(BadLine.objects.count(), 1)

        badline = BadLine.objects.all().first()
        self.assertEqual(badline.line_no, 19)
        self.assertEqual(badline.filename, "voter/test_data/2010-10-31T00-00-00/bad_not_enough.txt")
        self.assertEqual(badline.is_warning, False)
        self.assertIn("Less cells", badline.message)