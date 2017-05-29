from django.core.management import BaseCommand
from django.db import transaction
from django.forms.models import model_to_dict

import csv
import codecs
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
    with codecs.open(filename, "r", encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            non_empty_row = {k: v for k, v in row.items()
                             if not v.strip() == ''}
            yield non_empty_row


def find_model_and_existing_instance(file_tracker, row):
    data_file_kind = file_tracker.data_file_kind
    if data_file_kind == FileTracker.DATA_FILE_KIND_NCVOTER:
        model_class = NCVoter
        query_data = {"ncid": row['ncid'],
                      'model_name': data_file_kind}
    elif data_file_kind == FileTracker.DATA_FILE_KIND_NCVHIS:
        model_class = NCVHis
        query_data = {"ncid": row['ncid'],
                      'election_desc': row['election_desc'],
                      'model_name': data_file_kind}
    else:
        print("Unknown file format, aborting processing of {0}".format(file_tracker.filename))
        return None, None
    try:
        instance = ChangeTracker.objects.filter(**query_data).latest('file_tracker__created')
    except ChangeTracker.DoesNotExist:
        instance = None
    return model_class, instance


@transaction.atomic
def create_changes(output, file_tracker):
    if output:
        print("Processing change tracking for file {0}".format(file_tracker.filename))
    added_tally = 0
    modified_tally = 0
    ignored_tally = 0
    for index, row in enumerate(get_file_lines(file_tracker.filename)):
        if output:
            print(".", end='')
        hash_val = find_md5(row)
        model_class, change_tracker_instance = find_model_and_existing_instance(file_tracker, row)
        if model_class is None:
            # Can't determine file type, cancel processing
            return
        if change_tracker_instance is not None and change_tracker_instance.md5_hash == hash_val:
            # Nothing to do, data is up to date, move to next row
            ignored_tally += 1
            continue
        parsed_row = model_class.parse_row(row)
        if change_tracker_instance is None:
            ChangeTracker.objects.create(
                ncid=row['ncid'], election_desc=row.get('election_desc', ''),
                md5_hash=hash_val, file_tracker=file_tracker,
                model_name=file_tracker.data_file_kind,
                op_code=ChangeTracker.OP_CODE_ADD, data=row)
            added_tally += 1
        else:
            existing_data = model_class.parse_existing(change_tracker_instance.data)
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
def process_changes(output, file_tracker):
    if output:
        print("Processing updates for file {0}".format(file_tracker.filename))
    for change_tracker in file_tracker.changes.iterator():
        if output:
            print(".", end='')
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
            nc_voter = None
            if ModelClass == NCVHis:
                try:
                    nc_voter = NCVoter.objects.get(ncid=data['ncid'])
                except NCVoter.DoesNotExist:
                    nc_voter = None
            if nc_voter is not None:
                # TODO: Investigate if this works against real data
                ModelClass.objects.create(merge_dicts({"voter": nc_voter}, **data))
            else:
                ModelClass.objects.create(**data)
        if change_tracker.op_code == ChangeTracker.OP_CODE_MODIFY:
            if ModelClass == NCVHis:
                query_data = {
                    'ncid': change_tracker.ncid,
                    'election_desc': change_tracker.election_desc
                }
            else:
                query_data = {
                    'ncid': change_tracker.ncid,
                }
            ModelClass.objects.filter(**query_data) \
                .update(**data)
    file_tracker.updates_processed = True
    file_tracker.save()


def process_file(output, create_changes_only, data_file_label, data_file_kind, county_num=None):
    results = []
    if output:
        print("Processing {0} file...".format(data_file_label))
    file_tracker_filter_data = {
        'change_tracker_processed': False,
        'data_file_kind': data_file_kind
    }
    if county_num:
        file_tracker_filter_data['county_num'] = county_num
    file_trackers = FileTracker.objects.filter(**file_tracker_filter_data) \
        .order_by('created')
    for file_tracker in file_trackers:
        added, modified, ignored = create_changes(output, file_tracker)
        results.append(
            {'filename': file_tracker.filename,
             'file_tracker_id': file_tracker.id,
             'added': added,
             'modified': modified,
             'ignored': ignored})
        if output:
            print("Change tracking completed:")
            print("Added records: {0}".format(added))
            print("Modified records: {0}".format(modified))
            print("Ignored records: {0}".format(ignored))
        file_tracker.change_tracker_processed = True
        file_tracker.save()
    if not create_changes_only:
        for file_tracker in file_trackers:
            process_changes(output, file_tracker)
    return results


def process_files(output=False, create_changes_only=False, county_num=None):
    file_label_kind_listing = [("NCVoter", FileTracker.DATA_FILE_KIND_NCVOTER),
                               ("NCVHis", FileTracker.DATA_FILE_KIND_NCVHIS)]
    change_results = [
        process_file(output, create_changes_only,
                     data_file_label, data_file_kind, county_num)
        for data_file_label, data_file_kind in file_label_kind_listing
        ]
    # TODO: Add FK's from NCVoter to NCVHis once both are processed
    return change_results


class Command(BaseCommand):
    help = "Processes voter data to save into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            '-c', '--county',
            dest='county',
            type=int,
            help='The county number of the per-county file you want to process (Processes only this county, as opposed to all files)',)

    def handle(self, *args, **options):
        county_num = options.get('county')
        process_files(output=True, create_changes_only=False, county_num=county_num)
