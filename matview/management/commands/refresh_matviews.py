from functools import wraps
from threading import Lock

from django.core.management import BaseCommand
from django.db.models.signals import post_save

from matview.models import MatView


def synchronized(lock):
    """ Synchronization decorator. """

    @wraps(f)
    def wrap(f):
        def newFunction(*args, **kw):
            lock.acquire()
            try:
                return f(*args, **kw)
            finally:
                lock.release()
        return newFunction
    return wrap


class Command(BaseCommand):
    help = "Refresh all materialized views"

    def add_arguments(self, parser):
        parser.add_argument(
            '--threads', action='store', default=4, type=int,
            help="Number of worker threads to use"
        )

    def handle(self, *args, **options):
        matviews = MatView.objects.all()
        total = matviews.count()
        n = 1
        lock = Lock()

        @synchronized(lock)
        def report_update(sender, **kwargs):
            nonlocal n

            instance = kwargs.get('instance')
            if instance:
                delta = (instance.last_updated - instance._last_started).microseconds / 1000
                t = int(delta / options['threads'])
                if t >= 1000:
                    ts = "%0.1fs" % (t / 1000,)
                else:
                    ts = "%sms" % (t,)
                print("%s [%s %s/%s]" % (
                    instance.matview_name, ts, n, total,
                ))
                n += 1

        post_save.connect(report_update, sender=MatView)

        MatView.refresh_all(threads=options['threads'])
