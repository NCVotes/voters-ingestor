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
    for ncid in ChangeTracker.objects.filter(file_tracker_id=fileID).values_list('ncid',flat=True):
        if ncid not in processed_ncids:
            data=dict()
            for change in ChangeTracker.objects.filter(ncid=ncid,file_tracker_id__lt=fileID).order_by('snapshot_dt'):
                data.update(change.data)
            rebuilt_records.append((ncid,data))
            processed_ncids.add(ncid)
            if len(rebuilt_records)>BULK_CREATE_AMOUNT:
                for i in rebuilt_records:
                    NCVoter.objects.filter(ncid=i[0]).update(**(i[1]))
                rebuilt_records.clear()
    if len(rebuilt_records)>0:
        for i in rebuilt_records:
            NCVoter.objects.filter(ncid=i[0]).update(**(i[1]))
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
