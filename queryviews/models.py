import logging
from datetime import datetime

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.apps import apps
from django.db import models

from matview.dbutils import get_matview_name


logger = logging.getLogger(__name__)

queries = {}


def register_query(model, filters):
    name = get_matview_name(model, filters)
    app_label, model_name = model.split('.')

    if filters:
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

        # Instantiate a Model class with our generated name and attributes
        query_model = type(name, (models.Model,), attrs)
        # Register our generated model in our lookup registry
        queries.setdefault(app_label, {}).setdefault(model_name, {})[name] = query_model

    class Meta:
        managed = False
        db_table = name + '__count'
    attrs = {
        'count': models.IntegerField(),
        'Meta': Meta,
        '__module__': 'queryviews.models',
    }
    # Instantiate a Model class with our generated name and attributes
    count_model = type(name + '_count', (models.Model,), attrs)
    # Register our generated model in our lookup registry
    queries.setdefault(app_label, {}).setdefault(model_name, {})[name + '__count'] = count_model


def get_count(model, filters):
    name = get_matview_name(model, filters)
    app_label, model_name = model.split('.')
    try:
        count_model = queries[app_label][model_name][name + '__count']

        return count_model.objects.first().count
    except KeyError:
        # This is slower, potentially much slower! Log times for fallbacks.
        start = datetime.now()
        count = get_query(model, filters).count()
        elapsed = datetime.now() - start
        logger.warn(
            "get_count(%r, %r) had to do a potentially slow query. (%ssec)" %
            (model, filters, elapsed.seconds)
        )
        return count


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
        for k, v in query.filters.items():
            # Do not include the query if
            # - it filters on a field we don't care about
            # - it filters on a field we care about with a different value
            if k not in filters or filters[k] != v:
                break
        else:
            matches.append(query)
    if matches:
        # Find the match with the smallest count
        matches = sorted(matches, key=lambda query: get_count(model, query.filters))
        query = matches[0]
        remaining = {k: filters[k] for k in filters if k not in query.filters}
        return query.objects.filter(**{'data__' + k: v for k, v in remaining.items()})
    else:
        logger.warn(
            "get_query(%r, %r) had to do a potentially slow query against a source table." %
            (model, filters)
        )
        return apps.get_model(app_label, model_name).objects.filter(**{'data__' + k: v for k, v in filters.items()})


register_query("voter.NCVoter", {})
register_query("voter.NCVoter", {"party_cd": "DEM"})
register_query("voter.NCVoter", {"party_cd": "REP"})
register_query("voter.NCVoter", {"gender_code": "M"})
register_query("voter.NCVoter", {"gender_code": "F"})
register_query("voter.NCVoter", {"gender_code": "F", "party_cd": "REP"})
register_query("voter.NCVoter", {"gender_code": "M", "party_cd": "REP"})
register_query("voter.NCVoter", {"gender_code": "F", "party_cd": "DEM"})
register_query("voter.NCVoter", {"gender_code": "M", "party_cd": "DEM"})

for county in settings.COUNTIES:
    register_query("voter.NCVoter", {"county_desc": county})