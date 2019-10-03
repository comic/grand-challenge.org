from django.urls import path

from grandchallenge.algorithms.views import (
    AlgorithmImageList,
    AlgorithmImageCreate,
    AlgorithmImageDetail,
    AlgorithmExecutionSessionCreate,
)

app_name = "algorithms"

urlpatterns = [
    path("", AlgorithmImageList.as_view(), name="image-list"),
    path(
        "<slug:slug>/create/",
        AlgorithmImageCreate.as_view(),
        name="image-create",
    ),
    path("<slug:slug>/", AlgorithmImageDetail.as_view(), name="image-detail"),
    path(
        "<slug:slug>/run/",
        AlgorithmExecutionSessionCreate.as_view(),
        name="execution-session-create",
    ),
]
