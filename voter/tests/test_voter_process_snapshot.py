import datetime

from django.test import TestCase

from voter.models import FileTracker, ChangeTracker, NCVHis, NCVoter
from voter.management.commands.voter_process_snapshot import process_files, get_file_lines

file_trackers_data = [
    {"id": 1,
     "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
     "filename": "voter/test_data/2010-10-31T00-00-00/snapshot_latin1.txt",
     "data_file_kind": "NCVoter",
     "created": datetime.datetime(2011, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
     "change_tracker_processed": False,
    },
    {"id": 2,
     "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
     "filename": "voter/test_data/2010-10-31T00-00-00/snapshot_utf16.txt",
     "data_file_kind": "NCVoter",
     "created": datetime.datetime(2011, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
     "change_tracker_processed": False,
    },
    {"id": 3,
     "etag": "ab476ee500a0421dfab629e8dc464f2a-59",
     "filename": "voter/test_data/2011-10-31T00-00-00/snapshot.txt",
     "data_file_kind": "NCVoter",
     "created": datetime.datetime(2012, 4, 30, 1, 49, 28, 718731, tzinfo=datetime.timezone.utc),
     "change_tracker_processed": False,
    },
]


def create_file_tracker(i):
    FileTracker.objects.create(**file_trackers_data[i-1])


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

        for c in modifications:
            print(c.voter.ncid, c.data)
    
    def test_records_merge(self):
        self.load_two_snapshots()

        voter = NCVoter.objects.get(ncid="AS2035")
        data = voter.build_current()

        self.assertEqual(data["first_name"], 'PATRICIA')
        self.assertEqual(data["last_name"], 'WILSON')