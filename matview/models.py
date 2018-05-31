from threading import Thread
from django.utils import timezone

from django.db import transaction, connection
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder


def partition(lst, n):
    division = len(lst) / n
    return [lst[round(division * i):round(division * (i + 1))] for i in range(n)]


def update_matviews(matviews):
    for mv in matviews:
        mv.refresh()


def refresh_in_threads(matviews, threads):
    groups = partition(matviews, threads)
    threads = [Thread(target=update_matviews, args=(group,)) for group in groups]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


class MatView(models.Model):
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name="children")
    src_name = models.CharField(max_length=255)
    matview_name = models.CharField(max_length=255)
    filters = JSONField(encoder=DjangoJSONEncoder)
    last_updated = models.DateTimeField()

    def refresh(self):
        with transaction.atomic():
            with connection.cursor() as cursor:
                self._last_started = timezone.now()
                if self.filters:
                    cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY %s" % self.matview_name)
                cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY %s__count" % self.matview_name)
            self.last_updated = timezone.now()
            self.save()

        for child in self.children.all():
            child.refresh()

    @classmethod
    def refresh_all(cls, threads=1):
        tops = cls.objects.filter(parent=None)
        if threads == 1:
            for top in tops:
                top.refresh()
        else:
            refresh_in_threads(tops, threads)
