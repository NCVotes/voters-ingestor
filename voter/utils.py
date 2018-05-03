from datetime import datetime, timezone
from enum import Enum
import os
import subprocess

import requests

from voter.models import FileTracker


FETCH_STATUS_CODES = Enum("FETCH_STATUS_CODES",
                          "CODE_OK CODE_NET_FAILURE CODE_WRITE_FAILURE CODE_NOTHING_TO_DO")
FOLDER_DATETIME_FORMAT = "%Y%m%d%H%M%S"


def out(message, output):
    """
    Helper to send a message to the user. Wraps `print`, calling flush, but only
    if `output` is True.
    """
    if output:
        print(message, flush=True)


def tqdm_or_quiet(output):
    """Get our progress-bar generator OR a no-op if we're running in no-output mode."""
    if output:  # pragma: no cover
        from tqdm import tqdm
    else:
        def tqdm(x, **kw):
            return x
    return tqdm


def derive_target_folder(base_path, now):
    now_str = now.strftime(FOLDER_DATETIME_FORMAT)
    return os.path.join(base_path, now_str)


def get_etag_and_zip_stream(url):
    resp = requests.get(url, stream=True)
    etag = resp.headers.get('etag')
    return (etag, resp)


def write_stream(stream_response, filename, output=False):
    tqdm = tqdm_or_quiet(output)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    try:
        with open(filename, 'wb') as f:
            total = int(stream_response.headers['content-length']) / 1024
            for chunk in tqdm(stream_response.iter_content(chunk_size=1024), total=total):

                if chunk:
                    f.write(chunk)
    except IOError:
        return False
    return True


def extract_and_remove_file(filename):
    return_code = subprocess.call(['unzip', filename, '-d', os.path.dirname(filename)])
    if return_code != 0:
        return False
    else:
        # if unzip failed, then don't rm file so we can investigate
        os.remove(filename)
        return True


def attempt_fetch_and_write_new_zip(url, base_path, output=False):
    etag, resp = get_etag_and_zip_stream(url)
    now = datetime.now(timezone.utc)
    target_folder = derive_target_folder(base_path, now)
    target_filename = os.path.join(target_folder, url.split('/')[-1])
    f_track = FileTracker.objects.filter(etag=etag).first()
    if f_track:
        status_code = FETCH_STATUS_CODES.CODE_NOTHING_TO_DO
    else:
        if resp.status_code == 200:
            out("Fetching {0}".format(url), output)
            write_success = write_stream(resp, target_filename, output=output)
            if write_success:
                status_code = FETCH_STATUS_CODES.CODE_OK
            else:
                status_code = FETCH_STATUS_CODES.CODE_WRITE_FAILURE
        else:
            status_code = FETCH_STATUS_CODES.CODE_NET_FAILURE
    return (status_code, etag, now, target_filename)


def process_new_zip(url, base_path, label, county_num=None, output=False):
    out("Looking at {0}".format(url), output)

    fetch_status_code, etag, created_time, target_filename = attempt_fetch_and_write_new_zip(url, base_path, output)
    if fetch_status_code == FETCH_STATUS_CODES.CODE_OK:
        out("Fetched {0} successfully to {1}".format(url, target_filename), output)
        out("Extracting {0}".format(target_filename), output)
        unzip_success = extract_and_remove_file(target_filename)
        if unzip_success:
            target_dir = os.path.dirname(target_filename)
            for filename in os.listdir(target_dir):
                # Need to implement a warning system if there are multiple files
                if filename.endswith(".txt"):
                    result_filename = os.path.join(target_dir, filename)
                    out("Finished extracting to {0}".format(result_filename), output)
                    out("Updating FileTracker table", output)
                    if label == 'ncvoter':
                        data_file_kind = FileTracker.DATA_FILE_KIND_NCVOTER
                    else:
                        data_file_kind = FileTracker.DATA_FILE_KIND_NCVHIS
                    FileTracker.objects.create(
                        etag=etag, filename=result_filename,
                        county_num=county_num, created=created_time,
                        data_file_kind=data_file_kind)
                    out("Updated FileTracker table", output)
        else:
            out("Unable to unzip {0}".format(target_filename), output)
            return FETCH_STATUS_CODES.CODE_WRITE_FAILURE
    else:
        if fetch_status_code == FETCH_STATUS_CODES.CODE_NOTHING_TO_DO:
            out("File already downloaded", output)
        if fetch_status_code == FETCH_STATUS_CODES.CODE_NET_FAILURE:
            out("Unable to fetch file from {0}".format(url), output)
        if fetch_status_code == FETCH_STATUS_CODES.CODE_WRITE_FAILURE:
            out("Unable to write file to {0}".format(target_filename), output)
    return fetch_status_code
