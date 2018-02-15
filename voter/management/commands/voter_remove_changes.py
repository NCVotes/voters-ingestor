from django.core.management import BaseCommand
from django.db import transaction
from datetime import datetime
from voter.models import FileTracker, ChangeTracker, NCVoter
from chunkator import chunkator

BULK_CREATE_AMOUNT=3000

@transaction.atomic
def remove_changes(fileID):
    print("Rebuiding voter table", flush=True)
    processed_ncids=set()
    rebuilt_records=[]
    for row in chunkator(ChangeTracker.objects.filter(file_tracker_id=fileID), 1000):
        ncid=row['ncid']
        if ncid not in processed_ncids:
            data=dict()
            for change in ChangeTracker.objects.filter(ncid=ncid).order_by('snapshot_dt'):
                if change['file_tracker_id']<fileID:
                    data.update(change.data)
            rebuilt_records.append(data)
            processed_ncids.add(ncid)
            if len(rebuilt_records)>BULK_CREATE_AMOUNT:
                for i in rebuilt_records:
                    NCVoter.objects.filter(ncid=i['ncid']).update(**i)
                rebuilt_records.clear()
    if len(rebuilt_records)>0:
        for i in rebuilt_records:
            NCVoter.objects.filter(ncid=i['ncid']).update(**i)
        rebuilt_records.clear()
    print("Removing change trackers", flush=True)
    ChangeTracker.objects.filter(file_tracker_id=fileID).delete()


class Command(BaseCommand):
    help = "Rebuild the voter table until file ID"

    def add_arguments(self, parser):
        parser.add_argument(
            '--fileid',
            type=int,
            help='Rebuild the voter table until file ID')

    def handle(self, *args, **options):
        fileID=options['fileid']
        print('Removing all changes from file {}'.format(fileID),flush=True)
        remove_changes(fileID)
