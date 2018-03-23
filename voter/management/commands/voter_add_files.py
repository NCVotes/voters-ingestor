import os
import re
from datetime import datetime

from django.core.management import BaseCommand

from voter.models import FileTracker, BadLine


class Command(BaseCommand):
    help = "Process voter snapshot files and save them into the database"

    def add_arguments(self, parser):
        parser.add_argument('path', nargs='+', type=str)

        parser.add_argument(
            '--reset',
            action='store_true',
            dest='reset',
        )

    def handle(self, *args, **options):
        if options.get('reset'):
            FileTracker.objects.all().update(file_status=FileTracker.CANCELLED)

        filepaths = []
        for path in options.get('path', []):
            if os.path.isdir(path):
                for filepath in os.listdir(path):
                    filepaths.append(os.path.join(path, filepath))

        filepaths.sort(key=lambda fp: re.search(r'(\d{4})(\d{2})(\d{2})', fp).groups())

        for filepath in filepaths:
            ft, new = FileTracker.objects.get_or_create(
                filename=filepath,
                defaults={
                    'file_status': FileTracker.UNPROCESSED,
                    'etag': "",
                    'data_file_kind': FileTracker.DATA_FILE_KIND_NCVOTER,
                    'created': datetime.now(),
                },
            )

            if not new:
                if options.get('reset'):
                    ft.file_status = FileTracker.UNPROCESSED
                    ft.save()
                    BadLine.objects.filter(filename=ft.filename).delete()
                else:
                    print("REPEAT", filepath)
