from django.core.management import BaseCommand
from django.db import transaction
from django.forms.models import model_to_dict


import csv
import codecs
import hashlib
import os
from datetime import datetime
from bencode import bencode
import pytz
import time
from itertools import zip_longest

from voter.models import FileTracker, ChangeTracker, NCVoter

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
    deleted_data = {k: ('' if isinstance(x[k], str) else None) for k in x if k not in y}
    return merge_dicts(merge_dicts(new_data, modified_data), deleted_data)


def find_md5(row_data):
    "Given a dictionary of `row_data` returns the hex of its MD5 hash"
    row_data_str = bencode(row_data)
    row_data_b = bytes(row_data_str, 'utf-8')
    return hashlib.md5(row_data_b).hexdigest()


def get_file_lines(filename):
    with open(filename, "r", encoding='utf-8', errors='replace', newline='\r\n') as f:
        header = f.readline()
        header = header.split('\t')
        header = [i.strip().lower() for i in header]
        for row in f:
            l = row.split('\t')
            if len(l)==len(header):
                non_empty_row = {header[i]: l[i].strip() for i in range(len(header)) if not l[i].strip() == ''}
            elif len(l)>len(header):
                print("Extra fields found. Tell me the indices of the field that shall be ignored: (separated by space)")
                print(list(zip_longest(range(len(l)), l, header)))
                x=input()
                x=[int(i.strip()) for i in x.split()]
                x=set(x)
                l=[l[i] for i in range(len(l)) if i not in x]
                if len(l)!=len(header):
                    raise Exception("Number of fields still doesn't match header.")
                non_empty_row = {header[i]: l[i].strip() for i in range(len(header)) if not l[i].strip() == ''}
            else:
                print("Less fields found than header. Tell me the indices of the header that shall be ignored: (separated by space)")
                print(list(zip_longest(range(len(l)), header, l)))
                x=input()
                x=[int(i.strip()) for i in x.split()]
                x=set(x)
                header2=[header[i] for i in range(len(header)) if i not in x]
                if len(l)!=len(header2):
                    raise Exception("Number of fields still doesn't match header.")
                non_empty_row = {header2[i]: l[i].strip() for i in range(len(header2)) if not l[i].strip() == ''}
            yield non_empty_row


def find_existing_instance(file_tracker, row):
    ncid=row.get('ncid','')
    if ncid=='':
        return None, None, None
    try:
        voter_instance = NCVoter.objects.get(ncid=ncid)
    except NCVoter.DoesNotExist:
        voter_instance = None
    except NCVoter.MultipleObjectsReturned:
        print('Multiple voter records found for ncid {}!'.format(ncid))
        return None, None, None
    try:
        change_instance = ChangeTracker.objects.filter(ncid=ncid).latest('snapshot_dt')
    except ChangeTracker.DoesNotExist:
        change_instance = None

    return ncid, voter_instance, change_instance

@transaction.atomic
def lock_file(file_tracker):
    file_tracker.file_status=FileTracker.PROCESSING
    file_tracker.save()

@transaction.atomic
def reset_file(file_tracker):
    file_tracker.file_status=FileTracker.UNPROCESSED
    file_tracker.save()

@transaction.atomic
def track_changes(file_tracker, output):
    if output:
        print("Tracking changes for file {0}".format(file_tracker.filename))
    added_tally = 0
    modified_tally = 0
    ignored_tally = 0

    file_date = datetime.strptime(file_tracker.filename.split('/')[-1].split('_')[-1][:-4],'%Y%m%d').replace(tzinfo=pytz.timezone('US/Eastern'))
    for index, row in enumerate(get_file_lines(file_tracker.filename)):
        ncid, voter_instance, change_tracker_instance = find_existing_instance(file_tracker, row)
        if ncid is None:
            continue
        if (change_tracker_instance is None) != (voter_instance is None):
            print('Inconsistency: ncid {} is in one of the change and voter tables, but not in the other.'.format(ncid))
            raise
        hash_val = find_md5(row)
        if change_tracker_instance is not None and change_tracker_instance.md5_hash == hash_val:
            # Nothing to do, data is up to date, move to next row
            ignored_tally += 1
            continue
        parsed_row = NCVoter.parse_row(row)
        snapshot_dt = parsed_row.get('snapshot_dt')
        del parsed_row['snapshot_dt']
        if change_tracker_instance is None:
            change_tracker_data = parsed_row
            change_tracker_op_code = ChangeTracker.OP_CODE_ADD
            NCVoter.objects.create(**parsed_row)
            added_tally += 1
        else:
            existing_data = NCVoter.parse_existing(voter_instance)
            change_tracker_data = diff_dicts(existing_data, parsed_row)
            change_tracker_op_code = ChangeTracker.OP_CODE_MODIFY
            NCVoter.objects.filter(id=voter_instance.id).update(**change_tracker_data)
            modified_tally += 1
        change_tracker_values = {
            'ncid': row['ncid'],
            'md5_hash': hash_val,
            'file_tracker': file_tracker,
            'op_code': change_tracker_op_code,
            'data': change_tracker_data}
        if snapshot_dt:
            change_tracker_values['snapshot_dt']=snapshot_dt
        else:
            change_tracker_values['snapshot_dt']=file_date
        ChangeTracker.objects.create(**change_tracker_values)

    file_tracker.file_status = FileTracker.PROCESSED
    file_tracker.save()
    remove_files(file_tracker)
    return (added_tally, modified_tally, ignored_tally)


def process_files(output):
    if output:
        print("Processing NCVoter file...")

    while True:
        if FileTracker.objects.filter(file_status=FileTracker.PROCESSING).exists():
            print("Another parser is processing the files. Restart me later!")
            return

        file_tracker_filter_data = {
            'file_status': FileTracker.UNPROCESSED,
            'data_file_kind': FileTracker.DATA_FILE_KIND_NCVOTER
        }
        ncvoter_file_trackers = FileTracker.objects.filter(**file_tracker_filter_data).order_by('created')
        for file_tracker in ncvoter_file_trackers:
            lock_file(file_tracker)
            try:
                added, modified, ignored = track_changes(file_tracker,output)
            except:
                reset_file(file_tracker)
                raise Exception('Error processing file {}'.format(file_tracker.filename))
            if output:
                print("Change tracking completed for {}:".format(file_tracker.filename))
                print("Added records: {0}".format(added))
                print("Modified records: {0}".format(modified))
                print("Ignored records: {0}".format(ignored))

        time.sleep(3600)

    return


def remove_files(file_tracker,output=True):
    if output:
        print("Deleting processed file {}".format(file_tracker.filename))
    try:
        os.remove(file_tracker.filename)
    except FileNotFoundError:
        pass


class Command(BaseCommand):
    help = "Process voter data to save into the database"

    def handle(self, *args, **options):
        process_files(output=True)
