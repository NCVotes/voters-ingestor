import argparse
import time

from django.core.management import BaseCommand
from django.conf import settings

import botocore
import boto3
from collections import deque

from voter.utils import process_new_zip, out

s3client = boto3.client('s3')
s3client.meta.events.register('choose-signer.s3.*', botocore.handlers.disable_signing)


class Command(BaseCommand):
    help = """Fetch historical snapshots of voter data from NCSBE.gov

    E.g.

    no arg: download all available files that we have not already downloaded,
            then exit.
    --loop=N: download all available files that we have not already downloaded,
            then wait N minutes and start over.
    """

    def add_arguments(self, parser):
        # Don't rewrap the text in the help/description:
        parser.formatter_class = argparse.RawDescriptionHelpFormatter

        parser.add_argument(
            '--loop', action='store', type=int, default=0,
            help='After downloading, wait this many minutes and start over. Default is to stop after downloading.'
        )
        parser.add_argument(
            '--all', action='store_true', default=False,
            help='Download all available files. Default is to just download the first one that we have not'
                 'already downloaded.'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            dest='quiet',
            help='Do not output updates or progress while running',
        )

    def handle(self, *args, **options):
        output = not options.get('quiet')
        out("Fetching voter files...", output)
        while True:
            objects = s3client.list_objects(Bucket='dl.ncsbe.gov', Prefix='data/Snapshots/')
            filename_list = []
            for i in objects['Contents']:
                filename = i['Key'].split('/')[-1]
                ok = filename.endswith('.zip')
                if ok:
                    filename_list.append(filename)
            filename_list = sorted(filename_list)
            snapshots = deque()
            for l in filename_list:
                out(l, output)
                snapshots.append(settings.NCVOTER_HISTORICAL_SNAPSHOT_URL + l.strip())

            while len(snapshots) > 0:
                url = snapshots.popleft()
                process_new_zip(url, settings.NCVOTER_DOWNLOAD_PATH, "ncvoter", output=output)
            if not options['loop']:
                break
            else:  # pragma: no cover (infinite loop)
                minutes = options['loop']
                out("Sleep %d minutes..." % minutes, output)
                time.sleep(60 * minutes)
