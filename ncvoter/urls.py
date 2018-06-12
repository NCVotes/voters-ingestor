"""ncvoter URL Configuration"""
from django.urls import path, include
from django.contrib import admin
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('voter.urls')),

    path('drilldown/', include('drilldown.urls')),
]

if settings.ENVIRONMENT != "production":
    urlpatterns += [
        path('_qa/', include('qadashboard.urls')),
    ]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
