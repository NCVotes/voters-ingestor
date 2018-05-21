from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from matview.dbutils import get_matview_name


queries = {}


def register_query(model, filters):
    name = get_matview_name(model, filters)
    app_label, model_name = model.split('.')

    class Meta:
        managed = False
        db_table = name
    attrs = {
        'ncid': models.CharField('ncid', max_length=12),
        'data': JSONField(encoder=DjangoJSONEncoder),
        'Meta': Meta,
        '__module__': 'queryviews.models',
        'filters': filters,
    }
    query_model = type(name, (models.Model,), attrs)
    queries.setdefault(app_label, {}).setdefault(model_name, {})[name] = query_model

    class Meta:
        managed = False
        db_table = name + '__count'
    attrs = {
        'count': models.IntegerField(),
        'Meta': Meta,
        '__module__': 'queryviews.models',
    }
    count_model = type(name, (models.Model,), attrs)
    queries.setdefault(app_label, {}).setdefault(model_name, {})[name + '__count'] = count_model


def get_count(model, filters):
    name = get_matview_name(model, filters)
    app_label, model_name = model.split('.')
    count_model = queries[app_label][model_name][name + '__count']

    return count_model.objects.all().first().count


def get_query(model, filters):
    name = get_matview_name(model, filters)
    app_label, model_name = model.split('.')
    query_items = queries[app_label][model_name].items()

    # Find a materialized view query with the best match for the filter
    matches = []
    for name, query in query_items:
        if name.endswith('__count'):
            continue
        # Does the view have a subset of the query filters?
        match = True
        for k, v in query.filters.items():
            # Do not include the query if
            # - it filters on a field we don't care about
            # - it filters on a field we care about with a different value
            if k not in filters or filters[k] != v:
                match = False
                break
        if match:
            matches.append(query)
    if matches:
        # Find the match with the smallest count
        matches = sorted(matches, key=lambda query: get_count(model, query.filters))
        query = matches[0]
        remaining = {k: filters[k] for k in filters if k not in query.filters}
        return query.objects.filter(**{'data__'+k: v for k, v in remaining.items()})
    else:
        raise Exception("!?")


register_query("voter.NCVoter", {"party_cd": "DEM"})
register_query("voter.NCVoter", {"party_cd": "REP"})
register_query("voter.NCVoter", {"sex_code": "M"})
register_query("voter.NCVoter", {"sex_code": "F"})
register_query("voter.NCVoter", {"sex_code": "F", "party_cd": "REP"})
register_query("voter.NCVoter", {"sex_code": "M", "party_cd": "REP"})
register_query("voter.NCVoter", {"sex_code": "F", "party_cd": "DEM"})
register_query("voter.NCVoter", {"sex_code": "M", "party_cd": "DEM"})
