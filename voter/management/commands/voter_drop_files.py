import os
import argparse

from django.core.management import BaseCommand

from voter.models import FileTracker


class Command(BaseCommand):
    help = """Delete downloaded voter data files that have been processed."""

    def add_arguments(self, parser):
        # Don't rewrap the text in the help/description:
        parser.formatter_class = argparse.RawDescriptionHelpFormatter

        parser.add_argument(
            '--delete', action='store_true', default=False,
            help="Actually delete the files. Otherwise, just print them."
        )

        parser.add_argument(
            '--all', action='store_true', default=False,
            help="Find all files, not just processed ones."
        )

    def handle(self, *args, **options):
        print("File status legend:")
        print("[x] Exists")
        print("[m] Missing (already deleted)")
        print("[-] Deleted now")
        print()

        files = FileTracker.objects.filter(file_status=FileTracker.PROCESSED)
        if options['all']:
            files = FileTracker.objects.all()
        
        if files:
            for ft in files:
                exists = os.path.exists(ft.filename)
                mark = 'x' if exists else 'm'
                if exists and options['delete']:
                    os.unlink(ft.filename)
                    mark = '-'
                print("[{}] {}".format(mark, ft.filename))
        else:
            print("no files found")
