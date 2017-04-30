from django.core.management import BaseCommand

import csv
import hashlib

from bencode import bencode

from voter.models import FileTracker, ChangeTracker, NCVHis, NCVoter


def find_md5(row_data):
    "Given a dictionary of `row_data` returns the hex of its MD5 hash"
    row_data_str = bencode(row_data)
    row_data_b = bytes(row_data_str, 'utf-8')
    return hashlib.md5(row_data_b).hexdigest()


def get_file_lines(filename):
    with open(filename, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            non_empty_row = {k: v for k, v in row.items()
                             if not v.strip() == ''}
            yield non_empty_row


def find_model_and_existing_instance(file_tracker, row):
    if file_tracker.data_file_kind == FileTracker.DATA_FILE_KIND_NCVOTER:
        model_class = NCVoter
        ncid = row['ncid']
        instance = model_class.objects.filter(ncid=ncid).first()
    elif file_tracker.data_file_kind == FileTracker.DATA_FILE_KIND_NCVHIS:
        model_class = NCVHis
        ncid = row['ncid']
        election_desc = row['election_desc']
        instance = model_class.objects.filter(ncid=ncid,
                                                election_desc=election_desc).first()
    else:
        print("Unknown file format, aborting processing of {0}".format(file_tracker.filename))
        return None, None
    return model_class, instance


def process_file(file_tracker):
    for index, row in enumerate(get_file_lines(file_tracker.filename)):
        hash_val = find_md5(row)
        model_class, instance = find_model_and_existing_instance(file_tracker, row)
        if model_class is None:
            # Can't determine file type, cancel processing
            return
        if instance is not None and instance.md5_hash == hash_val:
            # Nothing to do, data is up to date, move to next row
            continue
        parsed_row = model_class.parse_row(row)
        if instance is None:
            pass
            # TODO: Create ChangeTracker with op_code A here
        else:
            pass
            # TODO: Create ChangeTracker with op_code M here
        print(hash_val, parsed_row)
    # TODO: Mark file_tracker.change_tracker_processed=True


class Command(BaseCommand):
    help = "Processes voter data to save into the database"

    def handle(self, *args, **options):
        fts = FileTracker.objects.filter(change_tracker_processed=False, data_file_kind='NCVHis') \
            .order_by('created')
        for ft in fts:
            process_file(ft)
