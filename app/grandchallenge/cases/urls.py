from django.urls import path

from grandchallenge.cases.views import (
    OSDImageDetail,
    RawImageUploadSessionDetail,
    RawImageUploadSessionList,
    VTKImageDetail,
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
    path(
        "images/<uuid:pk>/osd/",
        OSDImageDetail.as_view(),
        name="osd-image-detail",
    ),
    path(
        "images/<uuid:pk>/vtk/",
        VTKImageDetail.as_view(),
        name="vtk-image-detail",
    ),
]
