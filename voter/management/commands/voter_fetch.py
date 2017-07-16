from datetime import datetime, timezone
import os
from zipfile import ZipFile
from enum import Enum

from django.core.management import BaseCommand

import requests

from voter.models import FileTracker


NCVOTER_ZIP_URL_BASE = "http://dl.ncsbe.gov.s3.amazonaws.com/data/ncvoter"
NCVHIS_ZIP_URL_BASE = "http://dl.ncsbe.gov.s3.amazonaws.com/data/ncvhis"
NCVOTER_ZIP_URL = NCVOTER_ZIP_URL_BASE + "_Statewide.zip"
NCVHIS_ZIP_URL = NCVHIS_ZIP_URL_BASE + "_Statewide.zip"
NCVOTER_DOWNLOAD_PATH = "downloads/ncvoter"
NCVHIS_DOWNLOAD_PATH = "downloads/ncvhis"


pluck = lambda dict, *args: (dict[arg] for arg in args)

FETCH_STATUS_CODES = Enum("FETCH_STATUS_CODES",
                          "CODE_OK CODE_NET_FAILURE CODE_WRITE_FAILURE CODE_NOTHING_TO_DO CODE_DB_FAILURE")


def derive_target_folder(base_path, now):
    now_str = now.strftime("%Y-%m-%dT%H:%M:%S:%s")
    return os.path.join(base_path, now_str)


def get_etag_and_zip_stream(url):
    resp = requests.get(url, stream=True)
    etag = resp.headers.get('etag')
    return (etag, resp)


def write_stream(stream_response, filename):
    try:
        with open(filename, 'wb') as f:
            for chunk in stream_response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
    except IOError:
        return False
    return True


def extract_and_remove_file(filename):
    try:
        with ZipFile(filename, "r") as z:
            z.extractall(os.path.dirname(filename))
    except IOError:
        return False
    finally:
        os.remove(filename)
    return True


def attempt_fetch_and_write_new_zip(url, base_path):
    etag, resp = get_etag_and_zip_stream(url)
    now = datetime.now(timezone.utc)
    target_folder = derive_target_folder(base_path, now)
    target_filename = os.path.join(target_folder, url.split('/')[-1])
    f_track = FileTracker.objects.filter(etag=etag).first()
    if f_track:
        status_code = FETCH_STATUS_CODES.CODE_NOTHING_TO_DO
    else:
        if resp.status_code == 200:
            os.makedirs(target_folder, exist_ok=True)
            write_success = write_stream(resp, target_filename)
            if write_success:
                status_code = FETCH_STATUS_CODES.CODE_OK
            else:
                status_code = FETCH_STATUS_CODES.CODE_WRITE_FAILURE
        else:
            status_code = FETCH_STATUS_CODES.CODE_NET_FAILURE
    return {'status_code': status_code,
            'etag': etag,
            'created_time': now,
            'target_filename': target_filename}


def process_new_zip(url, base_path, label, county_num):
    print("Fetching {0}".format(label))
    fetch_status_code, target_filename, created_time, etag = pluck(
        attempt_fetch_and_write_new_zip(url, base_path),
        'status_code', 'target_filename', 'created_time', 'etag')
    if fetch_status_code == FETCH_STATUS_CODES.CODE_OK:
        print("Fetched {0} successfully to {1}".format(label, target_filename))
        print("Extracting {0}".format(target_filename))
        unzip_success = extract_and_remove_file(target_filename)
        if unzip_success:
            target_dir = os.path.dirname(target_filename)
            for filename in os.listdir(target_dir):
                if filename.endswith(".txt"):
                    result_filename = os.path.join(target_dir, filename)
                    print("Finished extracting to {0}".format(result_filename))
            print("Updating FileTracker table")
            if label == 'ncvoter':
                data_file_kind = FileTracker.DATA_FILE_KIND_NCVOTER
            else:
                data_file_kind = FileTracker.DATA_FILE_KIND_NCVHIS
            ft = FileTracker.objects.create(
                etag=etag, filename=target_filename[:-3] + 'txt',
                county_num=county_num, created=created_time,
                data_file_kind=data_file_kind)
            if not ft:
                return FETCH_STATUS_CODES.CODE_DB_FAILURE
        else:
            print("Unable to unzip {0}".format(target_filename))
            return FETCH_STATUS_CODES.CODE_WRITE_FAILURE
    else:
        if fetch_status_code == FETCH_STATUS_CODES.CODE_NET_FAILURE:
            print("Unable to fetch file from {0}".format(url))
        if fetch_status_code == FETCH_STATUS_CODES.CODE_WRITE_FAILURE:
            print("Unable to write file to {0}".format(target_filename))
        if fetch_status_code == FETCH_STATUS_CODES.CODE_NOTHING_TO_DO:
            print("Resource at {0} contains no new information. Nothing to do.".format(url))
    return fetch_status_code


class Command(BaseCommand):
    help = "Fetches and processes voter and voter history data from NCSBE.gov"

    def add_arguments(self, parser):
        parser.add_argument(
            '--bycounty',
            action='store_true',
            dest='bycounty',
            default=False,
            help='Fetch per county files rather than statewide',)

    def fetch_state_zips(self):
        status_1 = process_new_zip(NCVOTER_ZIP_URL, NCVOTER_DOWNLOAD_PATH, "ncvoter", None)
        status_2 = process_new_zip(NCVHIS_ZIP_URL, NCVHIS_DOWNLOAD_PATH, "ncvhis", None)
        return status_1, status_2

    def fetch_county_zips(self):
        statuses = []
        for county_num in range(1, 101):
            ncvoter_zip_url = NCVOTER_ZIP_URL_BASE + str(county_num) + ".zip"
            ncvhis_zip_url = NCVHIS_ZIP_URL_BASE + str(county_num) + ".zip"
            result = process_new_zip(ncvoter_zip_url,
                NCVOTER_DOWNLOAD_PATH, "ncvoter", county_num)
            statuses.append(result)
            result = process_new_zip(ncvhis_zip_url,
                NCVHIS_DOWNLOAD_PATH, "ncvhis", county_num)
            statuses.append(result)
        return statuses

    def handle(self, *args, **options):
        print("Fetching zip files...")
        if not options['bycounty']:
            status_1, status_2 = self.fetch_state_zips()
        else:
            self.fetch_county_zips()
