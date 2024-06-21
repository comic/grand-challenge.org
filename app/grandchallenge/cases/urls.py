from django.urls import path

from grandchallenge.cases.views import (
    CS3DImageDetail,
    CSImageDetail,
    ImageSearchView,
    ImageWidgetSelectView,
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
        "images/<uuid:pk>/cs/", CSImageDetail.as_view(), name="cs-image-detail"
    ),
    path(
        "select-image-widget/",
        ImageWidgetSelectView.as_view(),
        name="select-image-widget",
    ),
    path("images/search/", ImageSearchView.as_view(), name="image-search"),
    path(
        "images/<uuid:pk>/cs3d/",
        CS3DImageDetail.as_view(),
        name="cs3d-image-detail",
    ),
]
