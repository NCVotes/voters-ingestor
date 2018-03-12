from django.core.management import BaseCommand
from django.db import transaction


import hashlib
import os
from bencode import bencode

from itertools import zip_longest

from tqdm import tqdm

from voter.models import FileTracker, ChangeTracker, NCVoter

BULK_CREATE_AMOUNT = 500


def merge_dicts(x, y):
    """Given two dicts `x` and `y`, merge them into a new dict as a shallow
    copy and return it."""
    z = x.copy()
    z.update(y)
    return z


def diff_dicts(x, y):
    """Given dictionaries `x` and `y` returns a dictionairy with any key value
    pairs added or modified by `y` and any keys in `x` but not in `y` set to ''
    """
    new_data = {k: y[k] for k in y if k not in x}
    modified_data = {k: y[k] for k in y if k in x and y[k] != x[k]}
    deleted_data = {k: ('' if isinstance(x[k], str) else None) for k in x if k not in y}
    return merge_dicts(merge_dicts(new_data, modified_data), deleted_data)


def find_md5(row_data, exclude=[]):
    "Given a dictionary of `row_data` returns the hex of its MD5 hash"
    row = row_data.copy()
    for i in exclude:
        if i in row:
            del row[i]
    row_data_str = bencode(row)
    row_data_b = bytes(row_data_str, 'utf-8')
    return hashlib.md5(row_data_b).hexdigest()


def get_file_lines(filename):
    # guess the number of lines
    f = open(filename, 'rb')
    chunk = f.read(1024 * 1024)
    newlines_per_meg = chunk.count(b'\n')
    file_megs = os.stat(filename).st_size / (1024 * 1024)
    line_count = file_megs * newlines_per_meg

    # UTF16 or (presumably) BOM-less UTF8
    f.seek(0)
    if f.read(2) == b'\xff\xfe':
        encoding = 'utf16'
    else:
        encoding = 'latin1'

    f = open(filename, encoding=encoding)
    lines = iter(f)
    header = next(lines)
    header = header.replace('\x00', '')
    header = header.split('\t')
    header = [i.strip().lower() for i in header]

    counted = 0
    for row in tqdm(lines, total=line_count):
        counted += 1
        line = row.replace('\x00', '')
        line = line.split('\t')
        if len(line) == len(header):
            non_empty_row = {header[i]: line[i].strip() for i in range(len(header)) if not line[i].strip() == ''}
        elif len(line) == len(header) + 1:
            del line[45]
            non_empty_row = {header[i]: line[i].strip() for i in range(len(header)) if not line[i].strip() == ''}
        elif len(line) == len(header) + 3:
            x = set([45, 46, 47])
            line = [line[i] for i in range(len(line)) if i not in x]
            non_empty_row = {header[i]: line[i].strip() for i in range(len(header)) if not line[i].strip() == ''}
        elif len(line) > len(header):
            print("Extra fields found. Tell me the indices of the field that shall be ignored: (separated by space)")
            print(list(zip_longest(range(len(line)), line, header)))
            x = input()
            x = [int(i.strip()) for i in x.split()]
            x = set(x)
            line = [line[i] for i in range(len(line)) if i not in x]
            if len(line) != len(header):
                raise Exception("Number of fields still doesn't match header.")
            non_empty_row = {header[i]: line[i].strip() for i in range(len(header)) if not line[i].strip() == ''}
        else:
            print("Less fields found than header. Tell me the indices of the header that shall be ignored: (separated by space)")
            print(list(zip_longest(range(len(header)), header, line)))
            x = input()
            x = [int(i.strip()) for i in x.split()]
            x = set(x)
            header2 = [header[i] for i in range(len(header)) if i not in x]
            if len(line) != len(header2):
                raise Exception("Number of fields still doesn't match header.")
            non_empty_row = {header2[i]: line[i].strip() for i in range(len(header2)) if not line[i].strip() == ''}
        yield non_empty_row

    print("Decoded", counted, "lines from", filename)


def find_existing_instance(ncid):
    """Given an NCID find an existing NCVoter instance for that voter.

    Will prefetch all ChangeTracker instances related."""

    voter = NCVoter.objects.filter(ncid=ncid).prefetch_related('changelog').first()
    return voter


@transaction.atomic
def lock_file(file_tracker):
    file_tracker.file_status = FileTracker.PROCESSING
    file_tracker.save()


@transaction.atomic
def reset_file(file_tracker):
    file_tracker.file_status = FileTracker.UNPROCESSED
    file_tracker.save()


# @transaction.atomic
def track_changes(file_tracker, output):
    if output:
        print("Tracking changes for file {0}".format(file_tracker.filename), flush=True)
    added_tally = 0
    modified_tally = 0
    ignored_tally = 0
    skip_tally = 0
    total_lines = 0

    voter_records = []
    change_records = []
    voter_updates = []
    processed_ncids = set()

    def flush():
        with transaction.atomic():
            if voter_records:
                NCVoter.objects.bulk_create(voter_records)
        with transaction.atomic():
            for c in change_records:
                c.voter = c.voter
                c.voter_id = c.voter.id
            ChangeTracker.objects.bulk_create(change_records)
        change_records.clear()
        voter_records.clear()
        voter_updates.clear()
        processed_ncids.clear()

    for index, row in tqdm(enumerate(get_file_lines(file_tracker.filename))):
        total_lines += 1

        # If we see a repeat, flushed queued data before continuing
        # This prevents the same voter from appearing twice in a single bulkd insert
        ncid = row.get('ncid')
        if ncid in processed_ncids:
            flush()
        voter_instance = find_existing_instance(ncid)

        # Skip rows that have no NCID in them :-(
        # TODO: Log these so we can come back and figure out what to do with them
        if ncid is None:
            skip_tally += 1
            continue

        # Generate a hash value for the change set and skip this one if it matches
        # an existing change already recorded
        hash_val = find_md5(row, exclude=['snapshot_dt'])
        if voter_instance and voter_instance.changelog.filter(md5_hash=hash_val).exists():
            ignored_tally += 1
            continue

        # We're done skipping for various reasons, so lets move on to actually recording
        # new data. We start by parsing the the row data.
        parsed_row = NCVoter.parse_row(row)
        snapshot_dt = parsed_row.pop('snapshot_dt')

        # If there was no voter instance, this is an ADD otherwise a MODIFY
        # For modifying we only record a diff of data, otherwise all of it
        if voter_instance:
            modified_tally += 1
            change_tracker_op_code = 'M'
            existing_data = voter_instance.build_current()
            change_tracker_data = diff_dicts(existing_data, parsed_row)
        else:
            added_tally += 1
            change_tracker_op_code = 'A'
            change_tracker_data = parsed_row
            voter_instance = NCVoter.from_row(parsed_row)
            voter_records.append(voter_instance)

        # Queue the change up to be bulk inserted later
        change_records.append(ChangeTracker(
            voter = voter_instance,
            md5_hash = hash_val,
            snapshot_dt = snapshot_dt,
            file_tracker = file_tracker,
            file_lineno = total_lines,
            op_code = change_tracker_op_code,
            data = change_tracker_data,
        ))
        processed_ncids.add(ncid)

        # When the number of queued chanegs hits a threshold, we insert them all in bulk
        if len(change_records) >= BULK_CREATE_AMOUNT:
            flush()

    # Any left over records to flush that didn't hit the bulk amount?
    if change_records:
        flush()

    # Mark the file as processed, we're done with it
    file_tracker.file_status = FileTracker.PROCESSED
    file_tracker.save()

    # TODO: Add a way to skip this, if we want to re-run for testing without re-downloading
    # remove_files(file_tracker)
    if output:
        print("Total lines processed:", total_lines)
    return (added_tally, modified_tally, ignored_tally, skip_tally)


def process_files(output):
    if output:
        print("Processing NCVoter file...", flush=True)

    file_tracker_filter_data = {
        'file_status': FileTracker.UNPROCESSED,
        'data_file_kind': FileTracker.DATA_FILE_KIND_NCVOTER
    }
    # FOR TESTING
    FileTracker.objects.all().update(file_status=0)
    ncvoter_file_trackers = FileTracker.objects.filter(**file_tracker_filter_data).order_by('created')
    print(ncvoter_file_trackers.count(), "File Trackers")
    for file_tracker in ncvoter_file_trackers:
        if FileTracker.objects.filter(file_status=FileTracker.PROCESSING).exists():
            print("Another parser is processing the files. Restart me later!")
            return
        lock_file(file_tracker)
        try:
            added, modified, ignored, skipped = track_changes(file_tracker, output)
        except Exception:
            reset_file(file_tracker)
            raise Exception('Error processing file {}'.format(file_tracker.filename))
        except BaseException:
            reset_file(file_tracker)
            raise
        if output:
            print("Change tracking completed for {}:".format(file_tracker.filename))
            print("Added records: {0}".format(added))
            print("Modified records: {0}".format(modified))
            print("Skipped records: {0}".format(ignored))
            print("Ignored records: {0}".format(skipped), flush=True)

    return


def remove_files(file_tracker, output=True):
    if output:
        print("Deleting processed file {}".format(file_tracker.filename), flush=True)
    try:
        os.remove(file_tracker.filename)
    except FileNotFoundError:
        pass


class Command(BaseCommand):
    help = "Process voter snapshot files and save them into the database"

    def handle(self, *args, **options):
        process_files(output=True)
