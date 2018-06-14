from django.shortcuts import render

from drilldown.filters import ChoiceFilter, MultiChoiceFilter, AgeFilter, filters_from_request
from voter.models import NCVoter
from voter.constants import STATUS_FILTER_CHOICES, COUNTY_FILTER_CHOICES, GENDER_FILTER_CHOICES, \
    PARTY_FILTER_CHOICES, CITY_FILTER_CHOICES, RACE_FILTER_CHOICES


declared_filters = [
    ChoiceFilter(
        display_name='Status',
        field_name='status_cd',
        choices=STATUS_FILTER_CHOICES,
    ),
    ChoiceFilter(
        display_name='Gender',
        field_name='gender_code',
        choices=GENDER_FILTER_CHOICES,
    ),
    ChoiceFilter(
        display_name='Party',
        field_name='party_cd',
        choices=PARTY_FILTER_CHOICES,
    ),
    ChoiceFilter(
        display_name='County',
        field_name='county_id',
        choices=COUNTY_FILTER_CHOICES,
    ),
    ChoiceFilter(
        display_name='City',
        field_name='res_city_desc',
        choices=CITY_FILTER_CHOICES,
    ),
    MultiChoiceFilter(
        display_name='race',
        field_name='race_code',
        choices=RACE_FILTER_CHOICES,
    ),
    AgeFilter(),
]


def drilldown(request):
    applied_filters, final_filter_params = filters_from_request(declared_filters, request)
    unapplied_filters = [f for f in declared_filters if f.field_name not in applied_filters]
    total_count = NCVoter.get_count(filters={})

    return render(request, 'drilldown/drilldown.html', {
        "total_count": total_count,
        "applied_filters": applied_filters.values(),
        "unapplied_filters": unapplied_filters,
    })


def sample(request):
    applied_filters, final_filter_params = filters_from_request(declared_filters, request)
    sample_results = NCVoter.get_random_sample(final_filter_params, 20)
    total_count = NCVoter.get_count(filters={})

    return render(request, 'drilldown/sample.html', {
        "total_count": total_count,
        "applied_filters": applied_filters.values(),
        "sample_results": sample_results,
    })
