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
    for index, row in enumerate(get_file_lines(file_tracker.filename)):
        hash_val = find_md5(row)
        if file_tracker.data_file_kind == FileTracker.DATA_FILE_KIND_NCVOTER:
            parsed_row = NCVoter.parse_row(row)
        elif file_tracker.data_file_kind == FileTracker.DATA_FILE_KIND_NCVOTER:
            parsed_row = NCVHis.parse_row(row)
        else:
            return

        # TODO: Do processing of each row here
        print(hash_val, row)


class Command(BaseCommand):
    help = "Processes voter data to save into the database"

    def handle(self, *args, **options):
        fts = FileTracker.objects.filter(change_tracker_processed=False) \
            .order_by('created')
        for ft in fts:
            process_file(ft)
