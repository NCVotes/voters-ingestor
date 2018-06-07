import itertools
import logging
import random
import re
from copy import deepcopy
from datetime import datetime

from django.apps import apps
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from drilldown.filters import RaceFilter
from matview.dbutils import get_matview_name


logger = logging.getLogger(__name__)

# These variables get populated at server start: 'queries', 'filter_preps', 'flags'

# 'queries' is a nested lookup dictionary with the following structure:
# {
#     app_label: {
#         model_name: {
#             matview_name1: MatViewModel1,
#             matview_name2: MatViewModel2,
#             ...
#         },
#         ...
#     },
#     ...
# }
# when doing a query against a model, we look it up in this dictionary to find the best MatView
# (Materialized View) to use for the query.
queries = {}

# 'filter_preps' is a list of functions which map simple filters, like:
#     {'column-to-filter': 'value to be filtered'}
# to filters that are specialized to our materialized views. In most cases, we pass along
# the input filter unchanged, but for our 'flags' feature, we convert a simple filter like
# {'race_code': ['B', 'W']} into a filter that looks like {'raceflag_bw': 'true'}. This allows us
# to do an 'OR' query.
filter_preps = []
# 'flags' is a list of flags that we know about. When inspecting filters, we check to see if any
# match a flag, and if so, make sure we use the most efficient queries to filter for those flags.
flags = []
# 'filter_preps' and 'flags' are populated by the `register_flag` decorator


def register_query(model, filters):
    """
    Given a model and a list of filters, create an unmanaged Django model which uses an underlying
    materialized view that we've already created in the matview app.

    These are registered at server startup, populating the `queries` lookup dictionary, which is
    then used by get_query and get_count to find the right model to use.
    """
    matview_name = get_matview_name(model, filters)
    app_label, model_name = model.split('.')

    if filters:
        # create a Model for the 'query' materialized view
        class Meta:
            managed = False
            db_table = matview_name
        attrs = {
            'ncid': models.CharField('ncid', max_length=12),
            'data': JSONField(encoder=DjangoJSONEncoder),
            'Meta': Meta,
            '__module__': 'queryviews.models',
            'filters': filters,
        }

        # Instantiate a Model class with our generated name and attributes
        query_model = type(matview_name, (models.Model,), attrs)
        # Register our generated model in our lookup registry
        queries.setdefault(app_label, {}).setdefault(model_name, {})[matview_name] = query_model

    # create a Model for the special 'count' materialized view which holds just 1 row, containing a
    # count of records
    class Meta:
        managed = False
        db_table = matview_name + '__count'
    attrs = {
        'count': models.IntegerField(),
        'Meta': Meta,
        '__module__': 'queryviews.models',
    }
    # Instantiate a Model class with our generated name and attributes
    count_model = type(matview_name + '_count', (models.Model,), attrs)
    # Register our generated model in our lookup registry
    queries.setdefault(app_label, {}).setdefault(model_name, {})[matview_name + '__count'] = count_model


def register_flag(flagname):
    """Registers a "flag" and its filter_prep function.

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
    """
    Given user-requested list of filters, return filters that have been mapped to match the flags
    and filters in our our materialized views.
    """
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
    """
    Given a model and a list of filters, return a count of records which match that request.
    Simplistically, this would be `model.objects.filter(**filters).count()`, but since that would be
    too slow, we map the filters intelligently to our materialized views.

    If `fast_only` is True, then we ONLY return results from our materialized views and never drop
    down to the underlying table. This is mainly beneficial when testing.
    """
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
        # Log times for fallbacks, so we might identify them later to add more mat views
        logger.warning(
            "get_count(%r, %r) had to do a potentially slow query. (%s sec)",
            model, filters, elapsed.seconds
        )
        return count


def get_query(model, filters, fast_only=False):
    """
    Given a model and a list of filters, return a queryset of records which match that request.
    Simplistically, this would be `model.objects.filter(**filters)`, but since that would be
    too slow, we map the filters intelligently to our materialized views.

    If `fast_only` is True, then we ONLY return results from our materialized views and never drop
    down to the underlying table. This is mainly beneficial when testing.
    """
    filters = prepare_filters(filters)
    app_label, model_name = model.split('.')
    query_items = queries[app_label][model_name].items()

    if split_flag_filters(filters):
        raise ValueError("get_query() does not support complex flag queries!")

    # Find a materialized view query with the best match for the filter
    matches = []
    for name, query in query_items:
        if name.endswith('__count'):
            # skip the __count matviews since we're specifically looking for full rows
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
        q = models.Q(**{'data__' + k: v for k, v in filters.items()})
        start = datetime.now()
        queryset = apps.get_model(app_label, model_name).objects.filter(q)
        elapsed = datetime.now() - start
        logger.warn(
            "get_query(%r, %r) had to do a potentially slow query. (%s sec).",
            model, filters, elapsed.seconds
        )
        return queryset


def get_random_sample(n, model, filters):
    """Get up to `n` random sample rows from a query as efficiently as possible from a very large set."""

    # We need to find out if this is one filter or multiple sub-filters to combine
    sub_filters = split_flag_filters(filters)
    if sub_filters:
        # if we're getting a sample of 10 items from 3 groups, then we'll want 3 from groupA, 3 from
        # groupB and 4 from group C
        remainder = n % len(sub_filters)
        samples_each = [int(n / len(sub_filters)) for _ in sub_filters]
        s_i = random.randint(0, len(sub_filters) - 1)
        samples_each[s_i] += remainder
        sample = list(itertools.chain(*(
            get_random_sample(sub_n, model, sub_filter)
            for (sub_n, sub_filter) in zip(samples_each, sub_filters)
        )))
        random.shuffle(sample)
        return sample

    else:
        # First create the QuerySet from which we want to get a random sample
        # Our goal is to never actually execute this query
        query = get_query(model, filters)
        count = get_count(model, filters)
        if n >= count:
            return query
        offset = random.randint(0, count - n)
        return query[offset:offset + n]


# Register our queries

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

for status_code, status_label, status_desc in settings.STATUS_CHOICES:
    register_query("voter.NCVoter", {"voter_status_desc": status_code})


@register_flag("raceflag")
def map_to_raceflag(filters):
    race_code = filters.pop('race_code', None)
    if race_code:
        # race_code is give as a list of allowed values
        race_flag = 'raceflag_' + (''.join(sorted(race_code))).lower()
        filters[race_flag] = 'true'


for raceflag in RaceFilter.get_raceflags(2):
    # register race flags in all combos of <= 2 flags
    register_query("voter.NCVoter", {raceflag: "true"})
