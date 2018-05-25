"""ncvoter URL Configuration"""
from django.urls import path

from .views import drilldown


urlpatterns = [
    path('', drilldown),
]
