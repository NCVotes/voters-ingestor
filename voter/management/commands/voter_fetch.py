import argparse

from django.core.management import BaseCommand
from django.conf import settings

from voter.utils import process_new_zip, out


class Command(BaseCommand):
    help = """Fetches latest snapshots of voter and voter history data from NCSBE.gov

    E.g.

    no arg: fetch latest statewide voter and voter history snapshot.

    --bycounty: fetch county files rather than statewide
    --quiet: do not display any progress updates
    """

    def add_arguments(self, parser):
        # Don't rewrap the text in the help/description:
        parser.formatter_class = argparse.RawDescriptionHelpFormatter

        parser.add_argument(
            '--bycounty',
            action='store_true',
            dest='bycounty',
            default=False,
            help='Fetch per county files rather than statewide',)
        parser.add_argument(
            '--quiet',
            action='store_true',
            dest='quiet',
            help='Do not output updates or progress while running',
        )

    def fetch_state_zips(self, output=False):
        status_1 = process_new_zip(settings.NCVOTER_LATEST_STATEWIDE_URL, settings.NCVOTER_DOWNLOAD_PATH, "ncvoter", output=output)
        status_2 = process_new_zip(settings.NCVHIS_LATEST_STATEWIDE_URL, settings.NCVHIS_DOWNLOAD_PATH, "ncvhis", output=output)
        return status_1, status_2

    def fetch_county_zips(self, output=False):
        statuses = []
        for county_num in range(1, 101):
            ncvoter_zip_url = settings.NCVOTER_LATEST_COUNTY_URL_BASE + str(county_num) + ".zip"
            ncvhis_zip_url = settings.NCVHIS_LATEST_COUNTY_URL_BASE + str(county_num) + ".zip"
            result = process_new_zip(ncvoter_zip_url,
                                     settings.NCVOTER_DOWNLOAD_PATH, "ncvoter", county_num, output=output)
            statuses.append(result)
            result = process_new_zip(ncvhis_zip_url,
                                     settings.NCVHIS_DOWNLOAD_PATH, "ncvhis", county_num, output=output)
            statuses.append(result)
        return statuses

    def handle(self, *args, **options):
        output = not options.get('quiet')
        out("Fetching zip files...", output)
        if not options['bycounty']:
            status_1, status_2 = self.fetch_state_zips(output=output)
        else:
            self.fetch_county_zips(output=output)
