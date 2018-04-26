import datetime
from unittest import mock

from django.test import TestCase
import django.utils.timezone

from voter.models import FileTracker, ChangeTracker, NCVHis, NCVoter, BadLineRange
from voter.management.commands.voter_process_snapshot import process_files, get_file_lines, skip_or_voter, record_change, reset, diff_dicts, flush

file_trackers_data = [
    {
        "id": 1,
        "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
        "filename": "voter/test_data/2010-10-31T00-00-00/snapshot_latin1.txt",
        "data_file_kind": "NCVoter",
        "created": datetime.datetime(2011, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
    }, {
        "id": 2,
        "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
        "filename": "voter/test_data/2010-10-31T00-00-00/snapshot_utf16.txt",
        "data_file_kind": "NCVoter",
        "created": datetime.datetime(2011, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
    }, {
        "id": 3,
        "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
        "filename": "voter/test_data/2011-10-31T00-00-00/snapshot.txt",
        "data_file_kind": "NCVoter",
        "created": datetime.datetime(2012, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
    }, {
        "id": 4,
        "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
        "filename": "voter/test_data/2010-10-31T00-00-00/bad_extra45.txt",
        "data_file_kind": "NCVoter",
        "created": datetime.datetime(2011, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
    }, {
        "id": 5,
        "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
        "filename": "voter/test_data/2010-10-31T00-00-00/bad_extra45_46_47.txt",
        "data_file_kind": "NCVoter",
        "created": datetime.datetime(2011, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
    }, {
        "id": 6,
        "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
        "filename": "voter/test_data/2010-10-31T00-00-00/bad_extra_lots.txt",
        "data_file_kind": "NCVoter",
        "created": datetime.datetime(2011, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
    }, {
        "id": 7,
        "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
        "filename": "voter/test_data/2010-10-31T00-00-00/bad_not_enough.txt",
        "data_file_kind": "NCVoter",
        "created": datetime.datetime(2011, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
    }, {
        "id": 8,
        "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
        "filename": "voter/test_data/2010-10-31T00-00-00/snapshot_latin1_copy.txt",
        "data_file_kind": "NCVoter",
        "created": datetime.datetime(2011, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
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

    def load_two_snapshots(self):
        create_file_tracker(1)
        process_files(quiet=True)

        create_file_tracker(3)
        process_files(quiet=True)

    def load_same_two_snapshots(self):
        create_file_tracker(1)
        # Copy of same file, with snapshot_dt altered slightly
        create_file_tracker(8)
        process_files(quiet=True)

    def test_can_consume_latin1(self):
        create_file_tracker(1)
        process_files(quiet=True)

        # All NCVoter objects should be marked deleted=False
        self.assertEqual(NCVoter.objects.filter(deleted=False).count(), 19)

        # All inserted changes should be additions
        ncvoter_modifieds = ChangeTracker.objects.filter(op_code='A')
        self.assertEquals(ncvoter_modifieds.count(), 19)

        # Can find the first person from the snapshot
        c = ChangeTracker.objects.filter(data__last_name="THOMPSON", data__first_name="JESSICA").first()
        self.assert_(c)

    def test_can_consume_utf16(self):
        create_file_tracker(2)
        process_files(quiet=True)

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

        for voter in NCVoter.objects.all():
            self.assertEqual({}, diff_dicts(voter.build_current(), voter.data))

    def test_records_unchanged(self):
        self.load_same_two_snapshots()

        additions = ChangeTracker.objects.filter(op_code=ChangeTracker.OP_CODE_ADD)
        self.assertEquals(additions.count(), 19)

        for voter in NCVoter.objects.all():
            self.assertEqual({}, diff_dicts(voter.build_current(), voter.data))

    def test_records_merge(self):
        self.load_two_snapshots()

        voter = NCVoter.objects.get(ncid="AS2035")
        data = voter.build_current()
        change1, change2 = voter.changelog.all()

        self.assertEqual(change1.data["last_name"], 'LANGSTON')
        self.assertEqual(change2.data["last_name"], 'WILSON')

        self.assertEqual(data["first_name"], 'VON')
        self.assertEqual(data["last_name"], 'WILSON')

    def test_ignore_age(self):
        self.load_two_snapshots()

        voter = NCVoter.objects.get(ncid="AS2035")
        change1, change2 = voter.changelog.all()

        self.assertEqual('A', change1.op_code)
        self.assertEqual('68', change1.data.get('age'))
        self.assertIsNone(change2.data.get('age'))

    def test_can_resume_from_last_line(self):
        ft = create_file_tracker(1)
        ChangeTracker.objects.create(
            file_tracker=ft,
            file_lineno=10,
            data={},
            op_code='A',
            snapshot_dt=django.utils.timezone.now(),
            voter=NCVoter.objects.create(ncid="A1"),
        )
        process_files(quiet=True)

        ncvoter_modifieds = ChangeTracker.objects.filter(op_code='A')
        # 10 consumed, plus the one we made above
        self.assertEquals(ncvoter_modifieds.count(), 9 + 1)

    def test_can_resume_from_last_error(self):
        ft = create_file_tracker(1)
        BadLineRange.objects.create(
            filename=ft.filename,
            first_line_no=10,
            last_line_no=10,
            message="oops",
            example_line="data 1 2 3",
            is_warning=False,
        )
        process_files(quiet=True)

        ncvoter_modifieds = ChangeTracker.objects.filter(op_code='A')
        self.assertEquals(ncvoter_modifieds.count(), 9)

    def test_extra_data_cell_45(self):
        create_file_tracker(4)
        process_files(quiet=True)

        self.assertEquals(ChangeTracker.objects.count(), 19)
        self.assertEquals(BadLineRange.objects.count(), 1)

        badline = BadLineRange.objects.all().first()
        self.assertEqual(badline.last_line_no, 19)
        self.assertEqual(badline.filename, "voter/test_data/2010-10-31T00-00-00/bad_extra45.txt")
        self.assertEqual(badline.is_warning, True)
        self.assertIn("(removing 45)", badline.message)

    def test_extra_data_cell_45_46_47(self):
        create_file_tracker(5)
        process_files(quiet=True)

        self.assertEquals(ChangeTracker.objects.count(), 19)
        self.assertEquals(BadLineRange.objects.count(), 1)

        badline = BadLineRange.objects.all().first()
        self.assertEqual(badline.last_line_no, 19)
        self.assertEqual(badline.filename, "voter/test_data/2010-10-31T00-00-00/bad_extra45_46_47.txt")
        self.assertEqual(badline.is_warning, True)
        self.assertIn("(removing 45-47)", badline.message)

    def test_extra_data_cell_lots(self):
        create_file_tracker(6)
        process_files(quiet=True)

        # 18, because the bad line was an error and not processed
        self.assertEquals(ChangeTracker.objects.count(), 18)
        self.assertEquals(BadLineRange.objects.count(), 1)

        badline = BadLineRange.objects.all().first()
        self.assertEqual(badline.last_line_no, 19)
        self.assertEqual(badline.filename, "voter/test_data/2010-10-31T00-00-00/bad_extra_lots.txt")
        self.assertEqual(badline.is_warning, False)
        self.assertIn("More cells", badline.message)

    def test_extra_data_not_enough(self):
        create_file_tracker(7)
        process_files(quiet=True)

        # 18, because the bad line was an error and not processed
        self.assertEquals(ChangeTracker.objects.count(), 18)
        self.assertEquals(BadLineRange.objects.count(), 1)

        badline = BadLineRange.objects.all().first()
        self.assertEqual(badline.last_line_no, 19)
        self.assertEqual(badline.filename, "voter/test_data/2010-10-31T00-00-00/bad_not_enough.txt")
        self.assertEqual(badline.is_warning, False)
        self.assertIn("Less cells", badline.message)

    def test_error_recording_change(self):
        with mock.patch("voter.management.commands.voter_process_snapshot.prepare_change") as pc:
            pc.side_effect = Exception("Something went terribly wrong.")
            create_file_tracker(1)
            process_files(quiet=True)
        badline = BadLineRange.objects.all().first()

        self.assertIn("Exception: Something went terribly wrong", badline.message)
        self.assertIn("= prepare_change(", badline.message)

    def test_error_reprocessing_file_twice(self):
        create_file_tracker(7)

        process_files(quiet=True)
        process_files(quiet=True)

        self.assertEqual(1, BadLineRange.objects.all().count())

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

        with mock.patch("voter.management.commands.voter_process_snapshot.BULK_CREATE_AMOUNT", 10):
            with mock.patch("voter.management.commands.voter_process_snapshot.flush") as flush:
                flush.side_effect = reset  # minimal flush, no DB just reset the tracking variables

                process_files(quiet=True)

                self.assertEqual(2, flush.call_count)

    def test_flush_doesnt_reset_processed_ncids(self):
        "flush() should only reset change_records and voter_records, not processed_ncids"
        processed_ncids = set(['foo', 'bar'])
        with mock.patch('voter.management.commands.voter_process_snapshot.processed_ncids', processed_ncids):
            flush()
        self.assertEqual(processed_ncids, set(['foo', 'bar']))

    def test_unhandled_exceptions_reset(self):
        create_file_tracker(1)

        with mock.patch("voter.management.commands.voter_process_snapshot.track_changes") as track_changes:
            with mock.patch("voter.management.commands.voter_process_snapshot.reset_file") as reset_file:
                track_changes.side_effect = ValueError("oh no")
                self.assertRaises(Exception, process_files, quiet=True)
                self.assertEqual(1, reset_file.call_count)

    def test_unhandled_baseexceptions_reset(self):
        create_file_tracker(1)

        with mock.patch("voter.management.commands.voter_process_snapshot.track_changes") as track_changes:
            with mock.patch("voter.management.commands.voter_process_snapshot.reset_file") as reset_file:
                track_changes.side_effect = KeyboardInterrupt()
                process_files(quiet=True)
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

                process_files(quiet=True)
                self.assertEqual(0, track_changes.call_count)

    def test_line_numbers_across_files(self):
        ft0 = create_file_tracker(1)
        ft1 = create_file_tracker(2)
        process_files(quiet=True)
        # Each file's change tracker should start with line number 1
        ft0_first_tracker = ChangeTracker.objects.filter(file_tracker=ft0).order_by('file_lineno').first()
        self.assertEqual(1, ft0_first_tracker.file_lineno)
        ft1_first_tracker = ChangeTracker.objects.filter(file_tracker=ft1).order_by('file_lineno').first()
        self.assertEqual(1, ft1_first_tracker.file_lineno)
