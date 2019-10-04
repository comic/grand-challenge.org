from django.urls import path

from grandchallenge.algorithms.views import (
    AlgorithmImageCreate,
    AlgorithmImageDetail,
    AlgorithmExecutionSessionCreate,
    AlgorithmList,
    AlgorithmDetail,
    AlgorithmCreate,
    AlgorithmUpdate,
)

app_name = "algorithms"

urlpatterns = [
    path("", AlgorithmList.as_view(), name="list"),
    path("create/", AlgorithmCreate.as_view(), name="create"),
    path("<slug:slug>/", AlgorithmDetail.as_view(), name="detail"),
    path("<slug:slug>/update/", AlgorithmUpdate.as_view(), name="update"),
    path(
        "<slug:slug>/images/create/",
        AlgorithmImageCreate.as_view(),
        name="image-create",
    ),
    path(
        "<slug:slug>/images/<uuid:pk>/",
        AlgorithmImageDetail.as_view(),
        name="image-detail",
    ),
    path(
        "<slug:slug>/run/",
        AlgorithmExecutionSessionCreate.as_view(),
        name="execution-session-create",
    ),
]
