from django import template
from django.utils.safestring import mark_safe


register = template.Library()


@register.filter
def qs_trim(request, remove):
    """usage: {{ request|qs_trim:"key_to_remove" }}"""

    qs = request.GET.copy()
    try:
        del qs[remove]
    except KeyError:
        pass
    return mark_safe(qs.urlencode())
