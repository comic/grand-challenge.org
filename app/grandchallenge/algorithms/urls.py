from django.urls import path

from grandchallenge.algorithms.views import (
    AlgorithmCreate,
    AlgorithmDetail,
    AlgorithmExecutionSessionCreate,
    AlgorithmExecutionSessionDetail,
    AlgorithmExecutionSessionList,
    AlgorithmImageCreate,
    AlgorithmImageDetail,
    AlgorithmImageUpdate,
    AlgorithmJobUpdate,
    AlgorithmJobsList,
    AlgorithmList,
    AlgorithmPermissionRequestCreate,
    AlgorithmPermissionRequestList,
    AlgorithmPermissionRequestUpdate,
    AlgorithmUpdate,
    AlgorithmUserAutocomplete,
    EditorsUpdate,
    UsersUpdate,
)

app_name = "algorithms"

urlpatterns = [
    path("", AlgorithmList.as_view(), name="list"),
    path("create/", AlgorithmCreate.as_view(), name="create"),
    path(
        "users-autocomplete/",
        AlgorithmUserAutocomplete.as_view(),
        name="users-autocomplete",
    ),
    path("<slug>/", AlgorithmDetail.as_view(), name="detail"),
    path("<slug>/update/", AlgorithmUpdate.as_view(), name="update"),
    path(
        "<slug>/images/create/",
        AlgorithmImageCreate.as_view(),
        name="image-create",
    ),
    path(
        "<slug>/images/<uuid:pk>/",
        AlgorithmImageDetail.as_view(),
        name="image-detail",
    ),
    path(
        "<slug>/images/<uuid:pk>/update/",
        AlgorithmImageUpdate.as_view(),
        name="image-update",
    ),
    path(
        "<slug>/experiments/create/",
        AlgorithmExecutionSessionCreate.as_view(),
        name="execution-session-create",
    ),
    path(
        "<slug>/experiments/",
        AlgorithmExecutionSessionList.as_view(),
        name="execution-session-list",
    ),
    path(
        "<slug>/experiments/<uuid:pk>/",
        AlgorithmExecutionSessionDetail.as_view(),
        name="execution-session-detail",
    ),
    path("<slug>/jobs/", AlgorithmJobsList.as_view(), name="jobs-list"),
    path(
        "<slug>/jobs/<uuid:pk>/update/",
        AlgorithmJobUpdate.as_view(),
        name="job-update",
    ),
    path(
        "<slug>/editors/update/",
        EditorsUpdate.as_view(),
        name="editors-update",
    ),
    path("<slug>/users/update/", UsersUpdate.as_view(), name="users-update"),
    path(
        "<slug>/permission-requests/",
        AlgorithmPermissionRequestList.as_view(),
        name="permission-request-list",
    ),
    path(
        "<slug>/permission-requests/create/",
        AlgorithmPermissionRequestCreate.as_view(),
        name="permission-request-create",
    ),
    path(
        "<slug>/permission-requests/<int:pk>/update/",
        AlgorithmPermissionRequestUpdate.as_view(),
        name="permission-request-update",
    ),
]
