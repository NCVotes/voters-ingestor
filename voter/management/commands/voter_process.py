from django.core.management import BaseCommand
from django.db import transaction
from django.forms.models import model_to_dict

import csv
import codecs
import hashlib

from bencode import bencode

from voter.models import FileTracker, ChangeTracker, NCVHis, NCVoter


BULK_CREATE_AMOUNT = 3000


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
    unwritten_rows = []
    for index, row in enumerate(get_file_lines(file_tracker.filename)):
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
            change_tracker_data = row
            change_tracker_op_code = ChangeTracker.OP_CODE_ADD
            added_tally += 1
        else:
            existing_data = model_class.parse_existing(change_tracker_instance.data)
            change_tracker_data = diff_dicts(existing_data, parsed_row)
            change_tracker_op_code = ChangeTracker.OP_CODE_MODIFY
            modified_tally += 1
        change_tracker_values = {
            'ncid': row['ncid'],
            'election_desc': row.get('election_desc', ''),
            'md5_hash': hash_val,
            'file_tracker': file_tracker,
            'model_name': file_tracker.data_file_kind,
            'op_code': change_tracker_op_code,
            'data': change_tracker_data
        }
        unwritten_rows.append(ChangeTracker(**change_tracker_values))
        if len(unwritten_rows) >= BULK_CREATE_AMOUNT:
            if output:
                print(".", end='', flush=True)
            ChangeTracker.objects.bulk_create(unwritten_rows)
            unwritten_rows = []
    if len(unwritten_rows) > 0:
        ChangeTracker.objects.bulk_create(unwritten_rows)
        unwritten_rows = []
    file_tracker.change_tracker_processed = True
    file_tracker.save()
    return (added_tally, modified_tally, ignored_tally)


@transaction.atomic
def process_changes(output, file_tracker):
    if output:
        print("Processing updates for file {0}".format(file_tracker.filename))
    unwritten_ncvoters = []
    for index, change_tracker in enumerate(file_tracker.changes.iterator()):
        data = change_tracker.data
        if change_tracker.op_code == ChangeTracker.OP_CODE_ADD:
            unwritten_ncvoters.append(NCVoter(**data))
        if change_tracker.op_code == ChangeTracker.OP_CODE_MODIFY:
            NCVoter.objects.filter(ncid=change_tracker.ncid) \
                .update(**data)
        if len(unwritten_ncvoters) >= BULK_CREATE_AMOUNT:
            if output:
                print(".", end='', flush=True)
            NCVoter.objects.bulk_create(unwritten_ncvoters)
            unwritten_ncvoters = []
    if len(unwritten_ncvoters) >= 0:
        NCVoter.objects.bulk_create(unwritten_ncvoters)
        unwritten_ncvoters = []
    file_tracker.updates_processed = True
    file_tracker.save()


@transaction.atomic
def load_ncvhis(output, file_tracker):
    if output:
        print("Processing NCVHis data from file {0}".format(file_tracker.filename))
    added_tally = 0
    ignored_tally = 0
    unwritten_rows = []
    for index, row in enumerate(get_file_lines(file_tracker.filename)):
        ncid = row['ncid']
        election_desc = row['election_desc']
        try:
            existing_ncvhis = NCVHis.objects.get(ncid=ncid, election_desc=election_desc)
        except NCVHis.DoesNotExist:
            existing_ncvhis = None
        if existing_ncvhis is None:
            added_tally += 1
            parsed_row = NCVHis.parse_row(row)
            unwritten_rows.append(NCVHis(**parsed_row))
        else:
            ignored_tally += 1
            continue
        if len(unwritten_rows) >= BULK_CREATE_AMOUNT:
            if output:
                print(".", end='', flush=True)
            NCVHis.objects.bulk_create(unwritten_rows)
            unwritten_rows = []
    if len(unwritten_rows) > 0:
        NCVHis.objects.bulk_create(unwritten_rows)
        unwritten_rows = []
    file_tracker.change_tracker_processed = True
    file_tracker.updates_processed = True
    file_tracker.save()
    if output:
        print("NCVHis loading completed:")
        print("Added records: {0}".format(added_tally))
        print("Ignored records: {0}".format(ignored_tally))
    return (added_tally, 0, ignored_tally)


def process_files(output, county_num=None):
    results = []
    if output:
        print("Processing NCVoter file...")
    file_tracker_filter_data = {
        'change_tracker_processed': False,
        'data_file_kind': FileTracker.DATA_FILE_KIND_NCVOTER
    }
    if county_num:
        file_tracker_filter_data['county_num'] = county_num
    ncvoter_file_trackers = FileTracker.objects.filter(**file_tracker_filter_data) \
        .order_by('created')
    for file_tracker in ncvoter_file_trackers:
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
    file_tracker_filter_data['change_tracker_processed'] = True
    file_tracker_filter_data['updates_processed'] = False
    unprocessed_ncvoter_file_trackers = FileTracker.objects.filter(**file_tracker_filter_data) \
        .order_by('created')
    for file_tracker in unprocessed_ncvoter_file_trackers:
        process_changes(output, file_tracker)
    ncvhis_filter_data = {
        'change_tracker_processed': False,
        'updates_processed': False,
        'data_file_kind': FileTracker.DATA_FILE_KIND_NCVHIS,
    }
    if county_num:
        ncvhis_filter_data['county_num'] = county_num
    unloaded_ncvhis_file_trackers = FileTracker.objects.filter(**ncvhis_filter_data) \
        .order_by('created')
    ncvhis_results = []
    for file_tracker in unloaded_ncvhis_file_trackers:
        ncvhis_results.append(load_ncvhis(output, file_tracker))
    return results, ncvhis_results


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
        process_files(output=True, county_num=county_num)
