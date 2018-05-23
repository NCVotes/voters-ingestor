from django.core.management import BaseCommand
from django.utils import timezone
from django.db.models.signals import post_save

from matview.models import MatView


class Command(BaseCommand):
    help = "Refresh all materialized views"

    def handle(self, *args, **options):
        t = timezone.now()

        def report_update(sender, **kwargs):
            nonlocal t

            instance = kwargs.get('instance')
            delta = (instance.last_updated - t).seconds
            t = timezone.now()
            if instance:
                print("%s [%ss]" % (instance.matview_name, delta))

        post_save.connect(report_update, sender=MatView)
        MatView.refresh_all()
