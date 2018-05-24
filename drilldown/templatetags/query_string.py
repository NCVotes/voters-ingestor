from django import template
from django.utils.safestring import mark_safe


register = template.Library()


@register.simple_tag
def query_string(request, **kwargs):
    """usage: {% query_string request page=1 %}"""

    updated = request.GET.copy()

    for k, v in kwargs.iteritems():
        updated[k] = v

    return mark_safe(updated.urlencode())


@register.filter
def qs_trim(request, remove):
    """usage: {{ request|qs_trim:"key_to_remove" }}"""

    qs = request.GET.copy()
    try:
        del qs[remove]
    except KeyError:
        pass
    return mark_safe(qs.urlencode())
