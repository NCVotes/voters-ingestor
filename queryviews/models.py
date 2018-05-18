from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from matview.dbutils import get_matview_name


queries = {}


def add_query(filters):
    class Meta:
        managed = False
        db_table = get_matview_name(filters)
    attrs = {
        'ncid': models.CharField('ncid', max_length=12),
        'data': JSONField(encoder=DjangoJSONEncoder),
        'Meta': Meta,
        '__module__': 'queryviews.models',
        'filters': filters,
    }
    name = get_matview_name(filters)
    queries[name] = type(name, (models.Model,), attrs)


def get_query(filters):
    name = get_matview_name(filters)

    # Find a materialized view query with the best match for the filter
    match = False
    for name, query in queries.items():
        # Does the view have a subset of the query filters?
        match = True
        for k, v in query.filters.items():
            if filters[k] != v:
                match = False
                break
        if match:
            break
    if match:
        remaining = {k: filters[k] for k in filters if k not in query.filters}
        return query.objects.filter(**{'data__'+k: v for k, v in remaining.items()})
    else:
        raise Exception("!?")


add_query({"party_cd": "DEM"})
add_query({"party_cd": "REP"})
add_query({"sex_code": "M"})
add_query({"sex_code": "F"})
