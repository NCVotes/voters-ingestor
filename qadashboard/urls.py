from django.urls import path

from .views import qadashboard


urlpatterns = [
    path('', qadashboard),
]
