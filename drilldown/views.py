from django.shortcuts import render

from queryviews.models import get_count


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
    `filters` is a dictionary of the current `data` JSON field filters to find the final results
    `field` and `value` are a data entry to match in the results

    The new filter will be added to `filter_list` with the appropriate count and
    description, if available.
    """

    filters.update({field: value})

    name = "%s=%s" % (field, value)
    label = name
    description = name

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
