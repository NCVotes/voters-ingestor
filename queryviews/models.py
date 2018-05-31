import logging
import random
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


def get_random_sample(n, model, filters):
    """Get `n` random sample rows from a query as efficiently as possible from a very large set."""

    # First create the QuerySet from which we want to get a random sample
    # Our goal is to never actually execute this query
    query = get_query(model, filters)

    # Keep track of the sample as we build it
    sample_results = []

    # Find a range of ID numbers for the query and get a list of potential IDs
    # which we'll randomly shuffle
    low_id = query.values_list('id', flat=True).order_by('id').first()

    # Stop early if we get no IDs, which means there are no results to sample from
    if low_id is None:
        return []
    # We have some results to sample from, so continue

    high_id = query.values_list('id', flat=True).order_by('-id').first()
    seen = set()

    # Until we've found `n` samples or run out of IDs, try the shuffled IDs
    while len(sample_results) < n and len(seen) < (high_id - low_id):

        # Find the next possibly valid ID by picking a random number in the range
        # and then finding the next number which hasn't been used.
        i = random.randint(low_id, high_id)
        while i in seen:
            i = (i + 1) % (high_id + 1)
        # Don't use this again
        seen.add(i)

        # If this Voter ID exists in the database, add it to our sample list
        try:
            sample = query.get(id=i)
        except models.ObjectDoesNotExist:
            # Try the next one we haven't already looked at
            sample = query.filter(id__gt=i).exclude(id__in=seen).order_by('id').first()
            if not sample:
                continue
            seen.add(sample.id)
        sample_results.append(sample)

    return sample_results


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
