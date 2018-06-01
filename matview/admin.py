from django.contrib import admin

from matview.models import MatView


# In case we want to peek at our materialized views
admin.site.register(
    MatView,
    list_display=[
        'matview_name',
        'filters',
        'last_updated',
    ]
)
