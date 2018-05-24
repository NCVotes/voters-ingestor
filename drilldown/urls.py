"""ncvoter URL Configuration"""
from django.urls import path, include
from django.contrib import admin

from .views import drilldown


urlpatterns = [
    path('', drilldown),
]
