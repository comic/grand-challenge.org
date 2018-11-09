from django.urls import path

from grandchallenge.algorithms.forms import algorithm_upload_widget
from grandchallenge.algorithms.views import (
    AlgorithmList,
    AlgorithmCreate,
    AlgorithmDetail,
    AlgorithmExecutionSessionCreate,
)
from grandchallenge.cases.forms import upload_raw_files_widget

app_name = "algorithms"

urlpatterns = [
    path("", AlgorithmList.as_view(), name="list"),
    path("create/", AlgorithmCreate.as_view(), name="create"),
    path(
        f"create/{algorithm_upload_widget.ajax_target_path}",
        algorithm_upload_widget.handle_ajax,
        name="algorithm-upload-ajax",
    ),
    path("<slug:slug>/", AlgorithmDetail.as_view(), name="detail"),
    path(
        "<slug:slug>/run/",
        AlgorithmExecutionSessionCreate.as_view(),
        name="execution-session-create",
    ),
    path(
        f"<slug:slug>/run/{upload_raw_files_widget.ajax_target_path}",
        upload_raw_files_widget.handle_ajax,
        name="upload-execution-session-image-files-ajax",
    ),
]
