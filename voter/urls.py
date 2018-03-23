#!/usr/bin/env python3
"""voters app URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from .views import changes # VoterSampleView, VoterDetailView, voter_count

app_name = 'voters'
urlpatterns = [
    # path('', VoterSampleView.as_view(), name='sample'),
    # path('<int:pk>/', VoterDetailView.as_view(), name='detail'),
    # path('count/', voter_count)
    path('changes/', changes),
]