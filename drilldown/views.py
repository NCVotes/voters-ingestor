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
    filters.update({field: value})

    name = "%s=%s" % (field, value)
    label = name
    description = name

    # for F in FILTERS:
    #     if F['field'] == field and F['value'] == value:
    #         name = "%s: %s" % (F['facet'], F['label'])
    #         label = F['label']

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

    # add_filter(applied_filters, filters, "party_cd", "DEM")
    # add_filter(applied_filters, filters, "gender_code", "F")
    for field, value in request.GET.items():
        add_filter(applied_filters, filters, field, value)

    return render(request, 'drilldown/drilldown.html', {
        "total_count": get_count("voter.NCVoter", {}),
        "applied_filters": applied_filters,
    })
