# from rest_framework import viewsets
# import django_filters

# from voter.models import (
#     FileTracker, NCVoter, COUNTY_CODES, STATE_ABBREVS, RACE_CODES,
#     GENDER_CODES)
# from voter import serializers


# class FileTrackerFilterSet(django_filters.FilterSet):
#     created = django_filters.DateTimeFromToRangeFilter()

#     class Meta:
#         model = FileTracker
#         fields = ('created', 'data_file_kind', 'file_status',)


# class FileTrackerViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = FileTracker.objects.all()
#     serializer_class = serializers.FileTrackerSerializer
#     filter_class = FileTrackerFilterSet
#     order = ('created',)


# class NCVoterFilterSet(django_filters.FilterSet):
#     county_id = django_filters.ChoiceFilter(choices=COUNTY_CODES.items())
#     birth_age = django_filters.RangeFilter()
#     birth_state = django_filters.ChoiceFilter(choices=STATE_ABBREVS)
#     mail_state = django_filters.ChoiceFilter(choices=STATE_ABBREVS)
#     state_cd = django_filters.ChoiceFilter(choices=STATE_ABBREVS)
#     race_code = django_filters.ChoiceFilter(choices=RACE_CODES.items())
#     gender_code = django_filters.ChoiceFilter(choices=GENDER_CODES.items())
#     registr_dt = django_filters.DateTimeFromToRangeFilter()

#     class Meta:
#         model = NCVoter
#         # TODO: Add more relevant fields
#         fields = (
#             # Numeric Ranges
#             'birth_age',
#             # Datetime Ranges
#             'registr_dt',
#             # Booleans
#             'confidential_ind', 'drivers_lic',
#             # Enumerations
#             'birth_state', 'mail_state', 'state_cd',
#             'race_code', 'gender_code',
#             # Exact matches
#             'ncid', 'county_id',
#             'first_name', 'middle_name', 'last_name',
#             'voter_reg_num', 'status_cd', 'voter_status_desc',
#             'reason_cd',
#             'zip_code',
#             # TODO: Move this to Booleans once migrated
#             'absent_ind',
#         )


# class NCVoterViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = NCVoter.objects.all()
#     serializer_class = serializers.NCVoterSerializer
#     filter_class = NCVoterFilterSet
#     order = ('ncid',)


import json
from datetime import datetime
from django.http import JsonResponse
from voter.models import ChangeTracker


class Serializer(json.JSONEncoder):

    def __init__(self, *args, **kwargs):
        kwargs['indent'] = 2
        super().__init__(*args, **kwargs)

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError("Cannot serialize type '%s': %r" % (obj.__class__.__name__, obj))


def get_voter_basic(voter):
    d = voter.build_current()
    return {
        "full_name": ' '.join((
            d.get('first_name', ''),
            d.get('midl_name', ''),
            d.get('last_name', ''),
        )),
        "age": d['age'],
    }


def changes(request):
    start = datetime.now()
    changed = request.GET['changed']
    new = request.GET.get('new')
    limit = int(request.GET.get('limit', '10')) or None

    M = ChangeTracker.objects.filter(
        op_code=ChangeTracker.OP_CODE_MODIFY,
        data__has_key=changed,
    )\
        .prefetch_related('voter__changelog')\
        .order_by('voter__pk', '-snapshot_dt')\
        .distinct('voter__pk')

    M = M.exclude(**{'data__' + changed: ""})
    if new:
        M = M.filter(**{'data__' + changed: new})

    result = {}
    for c in M[:limit]:
        r = {}
        prev = c.get_prev()

        r["new"] = c.build_version()[changed]
        r["old"] = prev.build_version().get(changed, '') if prev else ''
        r["when"] = c.snapshot_dt
        r["voter"] = get_voter_basic(c.voter)

        result[c.voter.ncid] = r

    result['_elapsed'] = (datetime.now() - start).microseconds / 1000000

    return JsonResponse(result, encoder=Serializer)
