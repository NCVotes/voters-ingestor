"""ncvoter URL Configuration"""
from django.urls import path, include
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('voter.urls')),

    path('drilldown/', include('drilldown.urls')),
]
