from rest_framework import viewsets
import django_filters


from voter.models import (
        FileTracker, NCVoter, NCVHis,
        COUNTY_CODES, STATE_ABBREVS, RACE_CODES, GENDER_CODES)
from voter import serializers


class FileTrackerFilterSet(django_filters.FilterSet):
    created = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = FileTracker
        fields = ('created', 'data_file_kind', 'change_tracker_processed',
                  'updates_processed',)


class FileTrackerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FileTracker.objects.all()
    serializer_class = serializers.FileTrackerSerializer
    filter_class = FileTrackerFilterSet
    order = ('created',)


class NCVoterFilterSet(django_filters.FilterSet):
    county_id = django_filters.ChoiceFilter(choices=COUNTY_CODES.items())
    birth_age = django_filters.RangeFilter()
    birth_state = django_filters.ChoiceFilter(choices=STATE_ABBREVS)
    mail_state = django_filters.ChoiceFilter(choices=STATE_ABBREVS)
    state_cd = django_filters.ChoiceFilter(choices=STATE_ABBREVS)
    race_code = django_filters.ChoiceFilter(choices=RACE_CODES.items())
    gender_code = django_filters.ChoiceFilter(choices=GENDER_CODES.items())
    registr_dt = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = NCVoter
        # TODO: Add more relevant fields
        fields = (
            # Numeric Ranges
            'birth_age',
            # Datetime Ranges
            'registr_dt',
            # Booleans
            'confidential_ind', 'drivers_lic',
            # Enumerations
            'birth_state', 'mail_state', 'state_cd',
            'race_code', 'gender_code',
            # Exact matches
            'ncid', 'county_id',
            'first_name', 'middle_name', 'last_name',
            'voter_reg_num', 'status_cd', 'voter_status_desc',
            'reason_cd',
            'zip_code',
            # TODO: Move this to Booleans once migrated
            'absent_ind',
        )


class NCVoterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NCVoter.objects.all()
    serializer_class = serializers.NCVoterSerializer
    filter_class = NCVoterFilterSet
    order = ('ncid',)
