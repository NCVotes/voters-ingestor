from django.shortcuts import render

from queryviews.models import get_count


# When we implement filter interfaces we add labels and descriptions here
# FILTERS is a dictionary of all the data fields we can filter on
# For each field, there is a dictionary mapping possible values to text for the interface
# Availabel text items for each field/value pair is:
# - description: Text to display on the filter droppdown that describes how this
#   filter selects voters, such as "Who voted in the 2016 Primary". Can be HTML.
# - label: Display label for the value, which could be used in filter interfaces
FILTERS = {
    "gender_code": {
        "F": {
            "label": "Female",
            "description": "Who is <em>female</em>",
        },
        "M": {
            "label": "Male",
            "description": "Who is <em>male</em>",
        },
    },

    "party_cd": {
        "DEM": {
            "label": "Democrat",
            "description": "Who is a <em>Democrat</em>",
        },
        "REP": {
            "label": "Female",
            "description": "Who is a <em>Republican</em>",
        },
    },
}


def add_filter(filter_list, filters, field, value):
    """Add a filter to the filter list of the current drilldown.

    `filter_list` is a list of dictionaries describing the current filters
    `filters` is a dict added to by each call to add_filter(). This dict is passed to
        get_count() and get_query() to count and select voters.
    `field` and `value` are the key/value pair added to `filters` at this time

    The new filter will be added to `filter_list` with the appropriate count and
    description, if available. The dictionary added will have at least these keys:

    - `description` Text to display on the filter droppdown that describes how this
        filter selects voters, such as "Who voted in the 2016 Primary". Can be HTML.
    - `label` Display label for the value, which could be used in filter interfaces
    - `field` Data field being filtered on
    - `value` Data field value being filtered on
    - `count` Number of voters matching this filter *after* applying previous filters
    """

    filters.update({field: value})

    # Coded defaults for filters we haven't finished adding yet
    name = "%s=%s" % (field, value)
    label = name
    description = name
    # Nice labels/descriptions for filters we have fully implemented
    if field in FILTERS and value in FILTERS[field]:
        label = FILTERS[field][value]['label']
        description = FILTERS[field][value]['description']

    filter_list.append({
        "field": field,
        "value": value,
        "name": label,
        "count": get_count("voter.NCVoter", filters),
        "description": description,
    })


def drilldown(request):
    applied_filters = []
    filters = {}

    for field, value in request.GET.items():
        add_filter(applied_filters, filters, field, value)

    return render(request, 'drilldown/drilldown.html', {
        "total_count": get_count("voter.NCVoter", {}),
        "applied_filters": applied_filters,
    })
