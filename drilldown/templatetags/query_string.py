from django import template
from django.utils.safestring import mark_safe


register = template.Library()

@register.simple_tag
def query_string(request, **kwargs):
    """usages: {% query_transform request page=1 %}"""
    updated = request.GET.copy()

    for k, v in kwargs.iteritems():
        updated[k] = v

    return updated.urlencode()


@register.filter
def qs_trim(request, remove):
    qs = request.GET.copy()
    try:
        del qs[remove]
    except KeyError:
        pass
    return qs.urlencode()
