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


def process_file(file_tracker):
    filename = file_tracker.filename
    for index, row in enumerate(get_file_lines(filename)):
        hash_val = find_md5(row)
        if file_tracker.data_file_kind == FileTracker.DATA_FILE_KIND_NCVOTER:
            model_class = NCVoter
        elif file_tracker.data_file_kind == FileTracker.DATA_FILE_KIND_NCVHIS:
            model_class = NCVHis
        else:
            print("Unknown file format, aborting processing of {0}".format(filename))
            return
        # TODO: Search for nc_id in existing data, compare against hash_val
        parsed_row = model_class.parse_row(row)
        print(hash_val, parsed_row)


class Command(BaseCommand):
    help = "Processes voter data to save into the database"

    def handle(self, *args, **options):
        fts = FileTracker.objects.filter(change_tracker_processed=False, data_file_kind='NCVHis') \
            .order_by('created')
        for ft in fts:
            process_file(ft)
