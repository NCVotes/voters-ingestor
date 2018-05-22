from django.db import transaction, connection

from django.db import models
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder


class MatView(models.Model):
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name="children")
    src_name = models.CharField(max_length=255)
    matview_name = models.CharField(max_length=255)
    filters = JSONField(encoder=DjangoJSONEncoder)
    last_updated = models.DateTimeField(auto_now=True)

    def refresh(self):
        with transaction.atomic():
            with connection.cursor() as cursor:
                if self.filters:
                    cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY %s" % self.matview_name)
                cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY %s__count" % self.matview_name)
            self.save()

        for child in self.children.all():
            child.refresh()

    @classmethod
    def refresh_all(cls):
        tops = cls.objects.filter(parent=None)
        for top in tops:
            top.refresh()