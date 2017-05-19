"""ncvoter URL Configuration"""
from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.auth.models import User
from rest_framework import routers, serializers, viewsets

from rest_framework.urlpatterns import format_suffix_patterns
from voter import views

router = routers.DefaultRouter()


view_urlpatterns = [
    url(r'^files/$', views.FileTrackerList.as_view()),
    url(r'^files/(?P<pk>[0-9]+)/$', views.FileTrackerDetail.as_view()),
]

view_urlpatterns = format_suffix_patterns(view_urlpatterns)


urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^admin/', admin.site.urls),
]

urlpatterns.extend(view_urlpatterns)

