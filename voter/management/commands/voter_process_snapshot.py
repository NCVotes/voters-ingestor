from django.core.management import BaseCommand
from django.db import transaction


import hashlib
import os
import sys
import traceback
from bencode import bencode

from voter.models import FileTracker, BadLine, ChangeTracker, NCVoter

BULK_CREATE_AMOUNT = 500

voter_records = []
change_records = []
processed_ncids = set()

added_tally = 0
modified_tally = 0
ignored_tally = 0
skip_tally = 0
total_lines = 0


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


def tqdm_or_quiet(output):
    """Get our progress-bar generator OR a no-op if we're running in no-output mode."""

    if output:
        from tqdm import tqdm
    else:
        def tqdm(x, **kw):
            return x
    return tqdm


def guess_total_lines(filename):
    with open(filename, 'rb') as f:
        chunk = f.read(1024 * 1024)
        newlines_per_meg = chunk.count(b'\n')
        file_megs = os.stat(filename).st_size / (1024 * 1024)
        approx_line_count = file_megs * newlines_per_meg
        return approx_line_count


def get_file_encoding(filename):
    """We know how input data comes in latin1 and UTF-16 varieties, so we just
    check for a standard UTF-16 BOM to detect which one.
    """

    with open(filename, 'rb') as f:
        # UTF16 or latin1
        f.seek(0)
        if f.read(2) == b'\xff\xfe':
            encoding = 'utf16'
        else:
            encoding = 'latin1'
        return encoding


def get_file_lines(filename, output):
    tqdm = tqdm_or_quiet(output)

    # guess the number of lines and encoding
    approx_line_count = guess_total_lines(filename)
    encoding = get_file_encoding(filename)

    f = open(filename, encoding=encoding)
    lines = iter(f)
    header = next(lines)
    header = header.replace('\x00', '')
    header = header.split('\t')
    header = [i.strip().lower() for i in header]

    counted = 0
    for row in tqdm(lines, total=approx_line_count):
        counted += 1
        line = row.replace('\x00', '')
        line = line.split('\t')

        if len(line) == len(header):
            non_empty_row = {header[i]: line[i].strip() for i in range(len(header)) if not line[i].strip() == ''}

        elif len(line) == len(header) + 1:
            BadLine.warning(filename, counted, row, "Line has an extra 1 cell than the headers we have. (removing 45)")
            del line[45]
            non_empty_row = {header[i]: line[i].strip() for i in range(len(header)) if not line[i].strip() == ''}

        elif len(line) == len(header) + 3:
            BadLine.warning(filename, counted, row, "Line has an extra 3 cells than the headers we have. (removing 45-47)")
            x = set([45, 46, 47])
            line = [line[i] for i in range(len(line)) if i not in x]
            non_empty_row = {header[i]: line[i].strip() for i in range(len(header)) if not line[i].strip() == ''}

        elif len(line) > len(header):
            BadLine.error(filename, counted, row, "More cells in this line than we know what to do with.")
            continue

        else:
            BadLine.error(filename, counted, row, "Less cells in this line than we need.")
            continue

        yield counted, row, non_empty_row

    if output:
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


def flush():
    """Bulk insert pending NCVoter and ChangeTracker rows. Also, clear all such
    buffer lists.
    """
    with transaction.atomic():
        if voter_records:
            NCVoter.objects.bulk_create(voter_records)
    with transaction.atomic():
        # This looks weird. Let me explain.
        # All the unsaved ChangeTracker instances have references
        # to the NCVoter instances from *before* the NCVoter instances
        # were saved. So they do not know the voter instances now have
        # IDs from being inserted. This re-sets the voter on the change
        # object, ensuring it knows the ID of its voter and can be saved
        # properly.
        for c in change_records:
            c.voter = c.voter
            c.voter_id = c.voter.id
        ChangeTracker.objects.bulk_create(change_records)
    reset()


def reset():
    change_records.clear()
    voter_records.clear()
    processed_ncids.clear()


def skip_or_voter(row):
    global skip_tally
    global ignored_tally

    # If we see a repeat, flushed queued data before continuing
    # This prevents the same voter from appearing twice in a single bulk insert
    ncid = row.get('ncid')
    if ncid in processed_ncids:
        flush()
    voter_instance = find_existing_instance(ncid)

    # Skip rows that have no NCID in them :-(
    if not ncid:
        skip_tally += 1
        raise ValueError("No NCID found in data")

    # Generate a hash value for the change set and skip this one if it matches
    # an existing change already recorded
    hash_val = find_md5(row, exclude=['snapshot_dt'])
    if voter_instance and voter_instance.changelog.filter(md5_hash=hash_val).exists():
        ignored_tally += 1
        return None, None

    return ncid, voter_instance


def prepare_change(file_tracker, row, voter_instance):
    parsed_row = NCVoter.parse_row(row)
    snapshot_dt = parsed_row.pop('snapshot_dt')
    hash_val = find_md5(row, exclude=['snapshot_dt'])

    # If there was no voter instance, this is an ADD otherwise a MODIFY
    # For modifying we only record a diff of data, otherwise all of it
    if voter_instance:
        change_tracker_op_code = ChangeTracker.OP_CODE_MODIFY
        existing_data = voter_instance.build_current()
        change_tracker_data = diff_dicts(existing_data, parsed_row)
    else:
        change_tracker_op_code = ChangeTracker.OP_CODE_ADD
        change_tracker_data = parsed_row
        voter_instance = NCVoter.from_row(parsed_row)

    # Queue the change up to be bulk inserted later
    change = ChangeTracker(
        voter = voter_instance,
        md5_hash = hash_val,
        snapshot_dt = snapshot_dt,
        file_tracker = file_tracker,
        file_lineno = total_lines,
        op_code = change_tracker_op_code,
        data = change_tracker_data,
    )

    return change


def record_change(change):
    global added_tally
    global modified_tally

    if change.voter.pk:
        modified_tally += 1
    else:
        added_tally += 1
        voter_records.append(change.voter)
    change_records.append(change)
    processed_ncids.add(change.voter.ncid)


def track_changes(file_tracker, output):
    global added_tally
    global modified_tally
    global ignored_tally
    global skip_tally
    global total_lines

    if output:
        print("Tracking changes for file {0}".format(file_tracker.filename), flush=True)
    tqdm = tqdm_or_quiet(output)

    # Have we seen any lines, successful or failures, from this before?
    prev_lines = ChangeTracker.objects.filter(file_tracker=file_tracker)
    prev_errors = BadLine.objects.filter(filename=file_tracker.filename)

    last_line = 0
    if prev_lines.exists():
        last_line = prev_lines.order_by('-file_lineno')[0].file_lineno
    if prev_errors.exists():
        last_line = max(last_line, prev_errors.order_by('-line_no')[0].line_no)

    lines = get_file_lines(file_tracker.filename, output)

    for index, line, row in tqdm(lines):
        total_lines += 1
        if total_lines <= last_line:
            continue

        try:
            ncid, voter_instance = skip_or_voter(row)
            if not ncid:
                continue
        except ValueError as e:
            BadLine.error(file_tracker.filename, total_lines, line, e.args[0])
            continue

        # We're done skipping for various reasons, so lets move on to actually recording
        # new data. We start by parsing the the row data.
        try:
            change = prepare_change(file_tracker, row, voter_instance)
        except Exception:
            tb = ''.join(traceback.format_exception(*sys.exc_info()))
            BadLine.error(file_tracker.filename, total_lines, line, tb)
        else:
            record_change(change)

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

    ncvoter_file_trackers = FileTracker.objects.filter(**file_tracker_filter_data).order_by('created')

    for file_tracker in ncvoter_file_trackers:
        if FileTracker.objects.filter(file_status=FileTracker.PROCESSING).exists():
            if output:
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
