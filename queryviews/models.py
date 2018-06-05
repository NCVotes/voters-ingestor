import re
import itertools
import logging
import random
from copy import deepcopy
from datetime import datetime

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.apps import apps
from django.db import models

from matview.dbutils import get_matview_name
from drilldown.filters import RaceFilter


logger = logging.getLogger(__name__)


queries = {}
filter_preps = []
flags = []


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


def register_flag(flagname):
    """Registers a "flag" and its prep function.

    Used like this:

        @register_flag("raceflag")
        def map_to_raceflag(filters):
            race_code = filters.pop('race_code', None)
            if race_code:
                # race_code is give as a list of allowed values
                race_flag = 'raceflag_' + (''.join(race_code)).lower()
                filters[race_flag] = 'true'

    For example, this will replace any `race_code` field with an appropriate `raceflag_*`
    entries.
    """

    def _(callback):
        filter_preps.append(callback)
        flags.append(flagname)
    return _


def prepare_filters(filters):
    filters = deepcopy(filters)
    for func in filter_preps:
        func(filters)
    return filters


def split_flag_filters(filters):
    """Given a set of filters which may contain flags return a list of filters which
    are to be done in separate queries and combined.
    """

    filters = prepare_filters(filters)
    sub_filters = []
    for key in filters:
        if '_' not in key:
            continue
        for flagname in flags:
            flag = ''.join(sorted(key.split('_', 1)[1]))
            if key.startswith(flagname + '_'):
                if len(flag) <= 2:
                    filters.pop(key)
                    filters['%s_%s' % (flagname, flag)] = 'true' 
                else:
                    pairs = [x for x in re.split(r'(\w{2})', flag) if x]
                    for pair in pairs:
                        sub_filter = deepcopy(filters)
                        sub_filter[flagname + '_' + pair] = 'true'
                        sub_filter.pop(key)
                        sub_filters.append(sub_filter)
    return sub_filters


def get_count(model, filters, fast_only=False):
    filters = prepare_filters(filters)
    # First, assume we have a materialized view that already has the count we need
    name = get_matview_name(model, filters)
    app_label, model_name = model.split('.')
    # Attempt to read that materialized count
    try:
        sub_filters = split_flag_filters(filters)
        if sub_filters:
            count = 0
            for sub_filter in sub_filters:
                count += get_count(model, sub_filter, fast_only=fast_only)
            return count
        else:
            count_model = queries[app_label][model_name][name + '__count']
            return count_model.objects.first().count
    # If such a materialized count does not exist, we'll use get_query() to find the
    # most efficient way we can, but it'll still be slower... potentially much slower!
    except KeyError:
        if fast_only:
            raise ValueError("Refusing to do a slow query. (%r)" % (filters,))
        start = datetime.now()
        count = get_query(model, filters).count()
        elapsed = datetime.now() - start
        #  Log times for fallbacks, so we might identify them later to add more mat views
        logger.warning(
            "get_count(%r, %r) had to do a potentially slow query. (%ssec)" %
            (model, filters, elapsed.seconds)
        )
        return count


def get_query(model, filters, fast_only=False):
    filters = prepare_filters(filters)
    app_label, model_name = model.split('.')
    query_items = queries[app_label][model_name].items()

    if split_flag_filters(filters):
        raise ValueError("get_query() does not support complex flag queries!")

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
        q = models.Q(**{'data__' + k: v for k, v in remaining.items()})
        return query.objects.filter(q)
    else:
        if fast_only:
            raise ValueError("Refusing to do a slow query. (%r)" % (filters,))
        logger.warn(
            "get_query(%r, %r) had to do a potentially slow query against a source table." %
            (model, filters)
        )
        q = models.Q(**{'data__' + k: v for k, v in filters.items()})
        return apps.get_model(app_label, model_name).objects.filter(q)


def get_random_sample(n, model, filters):
    """Get up to `n` random sample rows from a query as efficiently as possible from a very large set."""

    # We need to find out if this is one filter or multiple sub-filters to combine
    sub_filters = split_flag_filters(filters)
    if sub_filters:
        remainder = n % len(sub_filters)
        samples_each = [int(n / len(sub_filters)) for _ in sub_filters]
        s_i = random.randint(0, len(sub_filters) - 1)
        samples_each[s_i] += remainder
        return list(itertools.chain(*(
            get_random_sample(sub_n, model, sub_filter)
            for (sub_n, sub_filter) in zip(samples_each, sub_filters)
        )))

    else:
        # First create the QuerySet from which we want to get a random sample
        # Our goal is to never actually execute this query
        query = get_query(model, filters)
        count = get_count(model, filters)
        if n >= count:
            return query
        offset = random.randint(0, count - n)
        return query[offset:offset + n]


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


@register_flag("raceflag")
def map_to_raceflag(filters):
    race_code = filters.pop('race_code', None)
    if race_code:
        # race_code is give as a list of allowed values
        race_flag = 'raceflag_' + (''.join(sorted(race_code))).lower()
        filters[race_flag] = 'true'


for raceflag in RaceFilter.get_raceflags(2):
    print("matview", raceflag)
    register_query("voter.NCVoter", {raceflag: "true"})
