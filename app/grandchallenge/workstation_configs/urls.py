from django.urls import path

from grandchallenge.workstation_configs.views import (
    WorkstationConfigCreate,
    WorkstationConfigDelete,
    WorkstationConfigDetail,
    WorkstationConfigList,
    WorkstationConfigUpdate,
)

app_name = "workstation-configs"

urlpatterns = [
    path("", WorkstationConfigList.as_view(), name="list"),
    path("create", WorkstationConfigCreate.as_view(), name="create"),
    path("<slug>/", WorkstationConfigDetail.as_view(), name="detail"),
    path("<slug>/delete/", WorkstationConfigDelete.as_view(), name="delete"),
    path("<slug>/update/", WorkstationConfigUpdate.as_view(), name="update"),
]
