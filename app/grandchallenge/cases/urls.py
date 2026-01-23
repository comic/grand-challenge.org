from django.urls import path

from grandchallenge.cases.views import (
    DICOMImageSetUploadDetail,
    DICOMImageSetUploadList,
    ImageSearchResultView,
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
    path(
        "dicom-uploads/",
        DICOMImageSetUploadList.as_view(),
        name="dicom-image-set-upload-list",
    ),
    path(
        "dicom-uploads/<uuid:pk>/",
        DICOMImageSetUploadDetail.as_view(),
        name="dicom-image-set-upload-detail",
    ),
    path(
        "images/search/", ImageSearchResultView.as_view(), name="image-search"
    ),
]
