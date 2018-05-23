from datetime import datetime, timezone

from django.core.management import BaseCommand
from django.db.models.signals import post_save

from matview.models import MatView


class Command(BaseCommand):
    help = "Refresh all materialized views"

    def handle(self, *args, **options):
        t = datetime.now(timezone.utc)

        def report_update(sender, **kwargs):
            nonlocal t

            instance = kwargs.get('instance')
            delta = (instance.last_updated - t).seconds
            t = datetime.now(timezone.utc)
            if instance:
                print("%s [%ss]" % (instance.matview_name, delta))

        post_save.connect(report_update, sender=MatView)
        MatView.refresh_all()
