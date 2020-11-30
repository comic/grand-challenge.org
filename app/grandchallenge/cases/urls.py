from django.urls import path

from grandchallenge.cases.views import (
    RawImageUploadSessionDetail,
    RawImageUploadSessionList,
)

app_name = "cases"

urlpatterns = [
    path(
        "uploads/",
        RawImageUploadSessionList.as_view(),
        name="raw-image-upload-session-list",
    ),
    path(
        "uploads/<uuid:pk>/",
        RawImageUploadSessionDetail.as_view(),
        name="raw-image-upload-session-detail",
    ),
]
