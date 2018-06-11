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


class MatView(object):
    pass
