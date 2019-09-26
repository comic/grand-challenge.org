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
    path("<slug:slug>/", AlgorithmImageDetail.as_view(), name="image-detail"),
    path(
        "<slug:slug>/run/",
        AlgorithmExecutionSessionCreate.as_view(),
        name="execution-session-create",
    ),
]
