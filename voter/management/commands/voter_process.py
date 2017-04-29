from django.core.management import BaseCommand

import csv
import hashlib

from bencode import bencode


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


def process_file(filename):
    for index, row in enumerate(get_file_lines(filename)):
        hash_val = find_md5(row)
        # TODO: Do processing of each row here
        print(hash_val, row)


class Command(BaseCommand):
    help = "Processes voter data to save into the database"

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str)

    def handle(self, *args, **options):
        filename = options.get('filename')
        if filename:
            process_file(filename)
        else:
            #TODO: determine latest filename downloaded from the database
            pass
