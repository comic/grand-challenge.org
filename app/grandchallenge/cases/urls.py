from django.urls import path

from grandchallenge.cases.forms import upload_raw_files_widget
from grandchallenge.cases.views import UploadRawFiles, ShowUploadSessionState

app_name = "cases"

urlpatterns = [
    path("uploads/", UploadRawFiles.as_view(), name="create"),
    path(
        f"uploads/{upload_raw_files_widget.ajax_target_path}",
        upload_raw_files_widget.handle_ajax,
        name="upload-raw-image-files-ajax",
    ),
    path(
        "uploads/<uuid:pk>/",
        ShowUploadSessionState.as_view(),
        name="raw-files-session-detail",
    ),
]
