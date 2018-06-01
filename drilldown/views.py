from django.conf import settings
from django.shortcuts import render

from drilldown.filters import ChoiceFilter, AgeFilter, filters_from_request
from ncvoter.known_cities import KNOWN_CITIES
from queryviews.models import get_count, get_random_sample


declared_filters = [
    ChoiceFilter(
        display_name='Status',
        field_name='voter_status_desc',
        choices=[
            ('ACTIVE', 'Active', "are actively registered"),
            ('DENIED', 'Denied', "were denied registration"),
            ('INACTIVE', 'Inactive', "have inactive registrations"),
            ('REMOVED', 'Removed', "have had their registration removed"),
            ('TEMPORARY', 'Temporary', 'have temporary registrations'),
        ]
    ),
    ChoiceFilter(
        display_name='Gender',
        field_name='gender_code',
        choices=[
            ('F', 'Female', "are <em>female</em>"),
            ('M', 'Male', "are <em>male</em>"),
        ]
    ),
    ChoiceFilter(
        display_name='Party',
        field_name='party_cd',
        choices=[
            ('DEM', "Democrat", "are <em>Democrats</em>"),
            ('REP', "Republican", "are <em>Republicans</em>"),
            ('UNA', 'Unaffiliated', "are <em>Unaffiliated</em>"),
        ]
    ),
    ChoiceFilter(
        display_name='County',
        field_name='county_desc',
        choices=[
            (county, county.title(), "live in <em>%s</em> county" % county.title())
            for county in settings.COUNTIES
        ]
    ),
    ChoiceFilter(
        display_name='City',
        field_name='res_city_desc',
        choices=[
            (city, city.title(), "live in <em>%s</em> " % city.title())
            for city in KNOWN_CITIES
        ]
    ),
    AgeFilter(),
]


def drilldown(request):
    applied_filters, final_filter_params = filters_from_request(declared_filters, request)
    unapplied_filters = [f for f in declared_filters if f.field_name not in applied_filters]

    total_count = get_count("voter.NCVoter", {})

    return render(request, 'drilldown/drilldown.html', {
        "total_count": total_count,
        "applied_filters": applied_filters.values(),
        "unapplied_filters": unapplied_filters,
    })


def sample(request):
    applied_filters, final_filter_params = filters_from_request(declared_filters, request)
    sample_results = get_random_sample(20, 'voter.NCVoter', final_filter_params)
    total_count = get_count("voter.NCVoter", {})

    return render(request, 'drilldown/sample.html', {
        "total_count": total_count,
        "applied_filters": applied_filters.values(),
        "sample_results": sample_results,
    })
