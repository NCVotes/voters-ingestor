"""ncvoter URL Configuration"""
from django.conf.urls import url, include
from django.contrib import admin

from rest_framework import routers

from voter import views


router = routers.DefaultRouter()

router.register(r'files', views.FileTrackerViewSet)
router.register(r'voters', views.NCVoterViewSet)


urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^admin/', admin.site.urls),
]
