from django.urls import path

from grandchallenge.workstations.views import (
    WorkstationList,
    WorkstationCreate,
    WorkstationDetail,
    WorkstationUpdate,
)

app_name = "workstations"

urlpatterns = [
    path("", WorkstationList.as_view(), name="list"),
    path("create/", WorkstationCreate.as_view(), name="create"),
    path("<slug>/", WorkstationDetail.as_view(), name="detail"),
    path("<slug>/update/", WorkstationUpdate.as_view(), name="update"),
]
