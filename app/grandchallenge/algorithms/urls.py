from django.urls import path

from grandchallenge.algorithms.forms import algorithm_image_upload_widget
from grandchallenge.algorithms.views import (
    AlgorithmImageList,
    AlgorithmImageCreate,
    AlgorithmImageDetail,
    AlgorithmExecutionSessionCreate,
)
from grandchallenge.cases.forms import upload_raw_files_widget

app_name = "algorithms"

urlpatterns = [
    path("", AlgorithmImageList.as_view(), name="image-list"),
    path("create/", AlgorithmImageCreate.as_view(), name="image-create"),
    path(
        f"create/{algorithm_image_upload_widget.ajax_target_path}",
        algorithm_image_upload_widget.handle_ajax,
        name="algorithm-image-upload-ajax",
    ),
    path("<slug:slug>/", AlgorithmImageDetail.as_view(), name="image-detail"),
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
