"""voters app URL Configuration"""
from django.urls import path
from .views import changes

urlpatterns = [
    path('changes/', changes),
]
