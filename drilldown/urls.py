from django.urls import path

from .views import drilldown, sample


urlpatterns = [
    path('', drilldown, name="drilldown"),
    path('sample/', sample, name="sample"),
]
