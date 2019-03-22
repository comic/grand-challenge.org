from django.urls import path

from grandchallenge.workstations.views import WorkstationsList

app_name = "workstations"

urlpatterns = [path("", WorkstationsList.as_view(), name="list")]
