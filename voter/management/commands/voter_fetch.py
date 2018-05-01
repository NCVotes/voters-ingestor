from django.core.management import BaseCommand
from django.conf import settings

from voter.utils import process_new_zip


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
        status_1 = process_new_zip(settings.NCVOTER_LATEST_STATEWIDE_URL, settings.NCVOTER_DOWNLOAD_PATH, "ncvoter", None)
        status_2 = process_new_zip(settings.NCVHIS_LATEST_STATEWIDE_URL, settings.NCVHIS_DOWNLOAD_PATH, "ncvhis", None)
        return status_1, status_2

    def fetch_county_zips(self):
        statuses = []
        for county_num in range(1, 101):
            ncvoter_zip_url = settings.NCVOTER_LATEST_COUNTY_URL_BASE + str(county_num) + ".zip"
            ncvhis_zip_url = settings.NCVHIS_LATEST_COUNTY_URL_BASE + str(county_num) + ".zip"
            result = process_new_zip(ncvoter_zip_url,
                                     settings.NCVOTER_DOWNLOAD_PATH, "ncvoter", county_num)
            statuses.append(result)
            result = process_new_zip(ncvhis_zip_url,
                                     settings.NCVHIS_DOWNLOAD_PATH, "ncvhis", county_num)
            statuses.append(result)
        return statuses

    def handle(self, *args, **options):
        print("Fetching zip files...")
        if not options['bycounty']:
            status_1, status_2 = self.fetch_state_zips()
        else:
            self.fetch_county_zips()
