#!/usr/bin/env python3
"""voters app URL Configuration
"""
from django.urls import path
from .views import changes

urlpatterns = [
    # path('', VoterSampleView.as_view(), name='sample'),
    # path('<int:pk>/', VoterDetailView.as_view(), name='detail'),
    # path('count/', voter_count)
    path('changes/', changes),
]
