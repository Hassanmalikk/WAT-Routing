from django.urls import path

from planner.api import api

urlpatterns = [path("api/", api.urls)]
