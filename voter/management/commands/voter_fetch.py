from datetime import datetime, timezone
import os
from zipfile import ZipFile

from django.core.management import BaseCommand

import requests


NCVOTER_ZIP_URL = "http://dl.ncsbe.gov.s3.amazonaws.com/data/ncvoter_Statewide.zip"
NCVHIS_ZIP_URL = "http://dl.ncsbe.gov.s3.amazonaws.com/data/ncvhis_Statewide.zip"
NCVOTER_DOWNLOAD_PATH = "downloads/ncvoter"
NCVHIS_DOWNLOAD_PATH = "downloads/ncvhis"


pluck = lambda dict, *args: (dict[arg] for arg in args)


def derive_target_folder(base_path):
    now = datetime.now(timezone.utc)
    now_str = now.strftime("%Y-%m-%dT%H:%M:%S")
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
        print("Failure writing to file {0}".format(filename))
        return False
    return True


def fetch_and_write_new_zip(url, base_path):
    etag, resp = get_etag_and_zip_stream(url)
    # TODO: Check here if etag has been seen and short-circuit if so
    target_folder = derive_target_folder(base_path)
    target_filename = os.path.join(target_folder, "data.zip")
    if resp.status_code == 200:
        os.makedirs(target_folder)
        return {'success': write_stream(resp, target_filename),
                'target_filename': target_filename}
    else:
        return {'success': False,
                'target_filename': target_filename}


def extract_and_remove_file(filename):
    try:
        with ZipFile(filename, "r") as z:
            z.extractall(os.path.dirname(filename))
    except IOError:
        print("Failure writing to file while extracting {0}".format(filename))
        return False
    finally:
        os.remove(filename)
    return True


def process_new_zip(url, base_path, label):
    print("Fetching {0}".format(label))
    success, target_filename = pluck(fetch_and_write_new_zip(url, base_path),
                                     'success', 'target_filename')
    if success:
        print("Fetched {0} successfully to {1}".format(label, target_filename))
        print("Extracting {0}".format(label))
        unzip_success = extract_and_remove_file(target_filename)
        if unzip_success:
            print("Finished extracting {0}".format(target_filename))


class Command(BaseCommand):
    help = "Fetches and processes voter and voter history data from NCSBE.gov"

    def fetch_zips(self):
        process_new_zip(NCVOTER_ZIP_URL, NCVOTER_DOWNLOAD_PATH, "ncvoter")
        process_new_zip(NCVHIS_ZIP_URL, NCVHIS_DOWNLOAD_PATH, "ncvhis")

    def handle(self, *args, **options):
        print("Fetching zip files...")
        self.fetch_zips()
