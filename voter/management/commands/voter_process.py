from django.core.management import BaseCommand
from django.db import transaction
from django.forms.models import model_to_dict

import csv
import hashlib

from bencode import bencode

from voter.models import FileTracker, ChangeTracker, NCVHis, NCVoter


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
    new_data = {k: y[k] for k in set(y) - set(x)}
    modified_data = {k: y[k] for k in y if k in x and y[k] != x[k]}
    deleted_data = {k: '' for k in x if k not in y}
    return merge_dicts(merge_dicts(new_data, modified_data), deleted_data)


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


@transaction.atomic
def process_file(file_tracker):
    print("Processing change tracking for file {0}".format(file_tracker.filename))
    added_tally = 0
    modified_tally = 0
    ignored_tally = 0
    for index, row in enumerate(get_file_lines(file_tracker.filename)):
        print(".", end='')
        hash_val = find_md5(row)
        model_class, instance = find_model_and_existing_instance(file_tracker, row)
        if model_class is None:
            # Can't determine file type, cancel processing
            return
        if instance is not None and instance.md5_hash == hash_val:
            # Nothing to do, data is up to date, move to next row
            ignored_tally += 1
            continue
        parsed_row = model_class.parse_row(row)
        if instance is None:
            ChangeTracker.objects.create(
                ncid=row['ncid'], election_desc=row.get('election_desc', ''),
                md5_hash=hash_val, file_tracker=file_tracker,
                model_name=file_tracker.data_file_kind,
                op_code=ChangeTracker.OP_CODE_ADD, data=row)
            added_tally += 1
        else:
            existing_data = model_to_dict(instance)
            data_diff = diff_dicts(existing_data, parsed_row)
            ChangeTracker.objects.create(
                ncid=row['ncid'], election_desc=row.get('election_desc', ''),
                md5_hash=hash_val, file_tracker=file_tracker,
                model_name=file_tracker.data_file_kind,
                op_code=ChangeTracker.OP_CODE_MODIFY, data=data_diff)
            modified_tally += 1
    file_tracker.change_tracker_processed = True
    file_tracker.save()
    return (added_tally, modified_tally, ignored_tally)


@transaction.atomic
def process_changes(file_tracker):
    print("Processing updates for file {0}".format(file_tracker.filename))
    for change_tracker in file_tracker.changes.iterator():
        ModelClass = None
        if change_tracker.model_name == FileTracker.DATA_FILE_KIND_NCVOTER:
            ModelClass = NCVoter
        if change_tracker.model_name == FileTracker.DATA_FILE_KIND_NCVHIS:
            ModelClass = NCVHis
        if ModelClass is None:
            print("invalid model_name value {0} in "
                  "ChangeTracker row with id {1}".format(
                      change_tracker.model_name, change_tracker.id))
            break
        data = change_tracker.data
        if change_tracker.op_code == ChangeTracker.OP_CODE_ADD:
            ModelClass.objects.create(**data)
        if change_tracker.op_code == ChangeTracker.OP_CODE_MODIFY:
            ModelClass.objects.filter(
                ncid=change_tracker.ncid,
                election_desc=change_tracker.election_desc) \
                .update(**data)
    file_tracker.updates_processed = True
    file_tracker.save()


class Command(BaseCommand):
    help = "Processes voter data to save into the database"

    def handle(self, *args, **options):
        for data_file_label, data_file_kind in [("NCVHis", FileTracker.DATA_FILE_KIND_NCVHIS),
                                                ("NCVoter", FileTracker.DATA_FILE_KIND_NCVOTER)]:
            print("Processing {0} files...".format(data_file_label))
            unprocessed_file_trackers = FileTracker.objects.filter(
                change_tracker_processed=False, data_file_kind=data_file_kind) \
                .order_by('created')
            for file_tracker in unprocessed_file_trackers:
                added, modified, ignored = process_file(file_tracker)
                print("Change tracking completed:")
                print("Added records: {0}".format(added))
                print("Modified records: {0}".format(modified))
                print("Ignored records: {0}".format(ignored))
            unupdated_file_trackers = FileTracker.objects.filter(
                change_tracker_processed=True, updates_processed=False,
                data_file_kind=data_file_kind) \
                .order_by('created')
            for file_tracker in unupdated_file_trackers:
                process_changes(file_tracker)