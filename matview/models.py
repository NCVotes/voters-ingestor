import datetime
import time

from django.db import transaction, connection

from django.db import models
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import pre_delete, pre_save
from django.db.models import ProtectedError


class MatView(models.Model):
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True)
    model_name = models.CharField(max_length=255)
    filters = JSONField(encoder=DjangoJSONEncoder)
    table_name = models.CharField(max_length=255)
    last_updated = models.DateTimeField(auto_now=True)

    @transaction.atomic
    def refresh_reports(self):
        with connection.cursor() as cursor:
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY %s" % self.table_name)
        self.save()


def forbid_outside_migrations(cls, sender, **kwargs):
    raise ProtectedError("Cannot modify MatView outside migration.")


pre_delete.connect(forbid_outside_migrations, sender=MatView)
pre_save.connect(forbid_outside_migrations, sender=MatView)
