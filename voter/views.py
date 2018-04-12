import json
from datetime import datetime
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
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
        "age": d.get('age', ''),
    }


def changes(request):
    """API endpoint that allows querying 100s+ millions of voter records to find changes
    a requestor might care about.

    Querystring Parameteres:
    `changed`       A data field to search for changes in between consecutive records for voters (required)
    `new`           Only find results where the field's new value matches this parameter (optional)
    `limit`         The number of voters to return, or fewer. (default: 10)
    """

    start = datetime.now()
    if 'changed' not in request.GET:
        return HttpResponseBadRequest('{"error": "`changed` is a required queryset parameter"}')
    changed = request.GET['changed']
    new = request.GET.get('new')
    limit = int(request.GET.get('limit', '10')) or None

    # Find change records that include the given field, only showing the most recent record
    # for each voter, but prefetching the related voter and their entire change history.
    mod_records = ChangeTracker.objects.filter(
        op_code=ChangeTracker.OP_CODE_MODIFY,
        data__has_key=changed,
    )\
        .prefetch_related('voter__changelog')\
        .order_by('voter__pk', '-snapshot_dt')\
        .distinct('voter__pk')

    # Don't include data that was just removed
    mod_records = mod_records.exclude(**{'data__' + changed: ""})

    # If requested, only include results where the field was changed to a specific new value
    # For example, changed=county_desc and new=DURHAM to find people who moved to Durham
    if new:
        mod_records = mod_records.filter(**{'data__' + changed: new})

    if request.GET.get('__debug'):
        return HttpResponse(mod_records.query)

    result = {}
    for c in mod_records[:limit]:
        r = {}
        prev = c.get_prev()

        r["new"] = c.build_version()[changed]
        r["old"] = prev.build_version().get(changed, '') if prev else ''
        r["when"] = c.snapshot_dt
        r["voter"] = get_voter_basic(c.voter)

        result[c.voter.ncid] = r

    result['_elapsed'] = (datetime.now() - start).total_seconds()

    return JsonResponse(result, encoder=Serializer)
