import datetime
from unittest import mock

from django.test import TestCase

from voter.models import FileTracker, BadLine, ChangeTracker, NCVHis, NCVoter
from voter.management.commands.voter_process_snapshot import process_files, get_file_lines, skip_or_voter, record_change, reset

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
    return FileTracker.objects.create(**file_trackers_data[i - 1])


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

    def setUp(self):
        reset()

    def tearDown(self):
        FileTracker.objects.all().delete()
        NCVoter.objects.all().delete()
        ChangeTracker.objects.all().delete()

    def load_two_snapshots(self):
        create_file_tracker(1)
        process_files(output=False)

        create_file_tracker(3)
        process_files(output=False)

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

    def test_extra_data_not_enough(self):
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

    def test_error_recording_change(self):
        with mock.patch("voter.management.commands.voter_process_snapshot.prepare_change") as pc:
            pc.side_effect = Exception("Something went terribly wrong.")
            create_file_tracker(1)
            process_files(output=False)
        badline = BadLine.objects.all().first()

        self.assertIn("Exception: Something went terribly wrong", badline.message)
        self.assertIn("= prepare_change(", badline.message)

    def test_error_reprocessing_file_twice(self):
        create_file_tracker(7)
        
        process_files(output=False)
        process_files(output=False)

        self.assertEqual(1, BadLine.objects.all().count())

    def test_flush_repeat_voter(self):
        """If the same voter appears twice within the span of the bulk-insert cutoff, we need
        to insert the previously seen data before continuing.
        """

        add = ChangeTracker(
            voter = NCVoter(ncid="A1"),
            md5_hash = "0000000000000000",
            snapshot_dt = "2000-01-01",
            file_tracker = create_file_tracker(1),
            file_lineno = 1,
            op_code = "A",
            data = {"first_name": "Mary", "last_name": "Godwin"},
        )

        modify = ChangeTracker(
            voter = NCVoter(ncid="A1"),
            md5_hash = "0000000000000001",
            snapshot_dt = "2001-01-01",
            file_tracker = add.file_tracker,
            file_lineno = 2,
            op_code = "M",
            data = {"first_name": "Mary", "last_name": "Shelley"},
        )

        with mock.patch("voter.management.commands.voter_process_snapshot.flush") as flush:
            skip_or_voter({"ncid": add.voter.ncid})
            record_change(add)
            self.assertEqual(0, flush.call_count)

            skip_or_voter({"ncid": modify.voter.ncid})
            record_change(modify)
            self.assertEqual(1, flush.call_count)

    def test_flush_at_bulk_limit(self):
        create_file_tracker(1)

        with mock.patch("voter.management.commands.voter_process_snapshot.BULK_CREATE_AMOUNT", 10) as _:  # noqa, F841
            with mock.patch("voter.management.commands.voter_process_snapshot.flush") as flush:
                flush.side_effect = reset  # minimal flush, no DB just reset the tracking variables

                process_files(output=False)

                self.assertEqual(2, flush.call_count)

    def test_unhandled_exceptions_reset(self):
        create_file_tracker(1)

        with mock.patch("voter.management.commands.voter_process_snapshot.track_changes") as track_changes:
            with mock.patch("voter.management.commands.voter_process_snapshot.reset_file") as reset_file:
                track_changes.side_effect = ValueError("oh no")
                self.assertRaises(Exception, process_files, output=False)
                self.assertEqual(1, reset_file.call_count)

    def test_unhandled_baseexceptions_reset(self):
        create_file_tracker(1)

        with mock.patch("voter.management.commands.voter_process_snapshot.track_changes") as track_changes:
            with mock.patch("voter.management.commands.voter_process_snapshot.reset_file") as reset_file:
                track_changes.side_effect = KeyboardInterrupt()
                self.assertRaises(KeyboardInterrupt, process_files, output=False)
                self.assertEqual(1, reset_file.call_count)

    def test_skip_in_processing_files(self):
        ft = create_file_tracker(1)
        ft.file_status = FileTracker.PROCESSING
        ft.save()

        with mock.patch("voter.management.commands.voter_process_snapshot.track_changes") as track_changes:
            with mock.patch("voter.management.commands.voter_process_snapshot.FileTracker.objects.filter") as filter:
                track_changes.side_effect = lambda *a: (0, 1, 2, 3)

                def filter_func(*a, **kw):
                    return FileTracker.objects.all()

                filter.side_effect = filter_func

                process_files(output=False)
                self.assertEqual(0, track_changes.call_count)
