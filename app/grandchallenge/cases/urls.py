from django.urls import path

from grandchallenge.cases.views import (
    ImageSearchResultView,
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
        "select-image-widget/",
        ImageWidgetSelectView.as_view(),
        name="select-image-widget",
    ),
    path(
        "images/search/", ImageSearchResultView.as_view(), name="image-search"
    ),
]
