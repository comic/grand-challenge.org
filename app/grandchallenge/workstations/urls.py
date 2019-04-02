from django.urls import path

from grandchallenge.workstations.forms import workstation_image_upload_widget
from grandchallenge.workstations.views import (
    WorkstationList,
    WorkstationCreate,
    WorkstationDetail,
    WorkstationUpdate,
    WorkstationImageCreate,
    WorkstationImageDetail,
    SessionCreate,
    SessionDetail,
    SessionUpdate,
)

app_name = "workstations"

urlpatterns = [
    path("", WorkstationList.as_view(), name="list"),
    path("create/", WorkstationCreate.as_view(), name="create"),
    path("<slug>/", WorkstationDetail.as_view(), name="detail"),
    path("<slug>/update/", WorkstationUpdate.as_view(), name="update"),
    path(
        "<slug>/images/create/",
        WorkstationImageCreate.as_view(),
        name="image-create",
    ),
    path(
        f"<slug>/images/create/{workstation_image_upload_widget.ajax_target_path}",
        workstation_image_upload_widget.handle_ajax,
        name="image-upload-ajax",
    ),
    path(
        "<slug>/images/<uuid:pk>/",
        WorkstationImageDetail.as_view(),
        name="image-detail",
    ),
    path(
        "<slug>/session/create/",
        SessionCreate.as_view(),
        name="session-create",
    ),
    path(
        "<slug>/session/<uuid:pk>/",
        SessionDetail.as_view(),
        name="session-detail",
    ),
    path(
        "<slug>/session/<uuid:pk>/update/",
        SessionUpdate.as_view(),
        name="session-update",
    ),
]
