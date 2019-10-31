from django.urls import path

from grandchallenge.cases.views import (
    ShowUploadSessionState,
    UploadRawFiles,
    show_image,
)

app_name = "cases"

urlpatterns = [
    path("uploads/", UploadRawFiles.as_view(), name="create"),
    path(
        "uploads/<uuid:pk>/",
        ShowUploadSessionState.as_view(),
        name="raw-files-session-detail",
    ),
    path("uploads/show_image/<uuid:pk>/", show_image, name="show_image"),
]
