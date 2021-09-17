from django.urls import path

from grandchallenge.algorithms.views import (
    AlgorithmAddRepo,
    AlgorithmCreate,
    AlgorithmDetail,
    AlgorithmExecutionSessionCreate,
    AlgorithmExecutionSessionDetail,
    AlgorithmExperimentCreate,
    AlgorithmImageCreate,
    AlgorithmImageDetail,
    AlgorithmImageUpdate,
    AlgorithmList,
    AlgorithmPermissionRequestCreate,
    AlgorithmPermissionRequestList,
    AlgorithmPermissionRequestUpdate,
    AlgorithmUpdate,
    ComponentInterfaceList,
    EditorsUpdate,
    JobDetail,
    JobExperimentDetail,
    JobUpdate,
    JobViewersUpdate,
    JobsList,
    UsersUpdate,
)

app_name = "algorithms"

urlpatterns = [
    path("", AlgorithmList.as_view(), name="list"),
    path("create/", AlgorithmCreate.as_view(), name="create"),
    path(
        "interfaces/",
        ComponentInterfaceList.as_view(),
        name="component-interface-list",
    ),
    path("<slug>/", AlgorithmDetail.as_view(), name="detail"),
    path("<slug>/update/", AlgorithmUpdate.as_view(), name="update"),
    path("<slug>/add-repo/", AlgorithmAddRepo.as_view(), name="add-repo"),
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
        "<slug>/experiments/create/flex/",
        AlgorithmExperimentCreate.as_view(),
        name="execution-session-create-new",
    ),
    path(
        "<slug>/experiments/<uuid:pk>/",
        AlgorithmExecutionSessionDetail.as_view(),
        name="execution-session-detail",
    ),
    path("<slug>/jobs/", JobsList.as_view(), name="job-list"),
    path("<slug>/jobs/<uuid:pk>/", JobDetail.as_view(), name="job-detail",),
    path(
        "<slug>/jobs/<uuid:pk>/update/",
        JobUpdate.as_view(),
        name="job-update",
    ),
    path(
        "<slug>/jobs/<uuid:pk>/experiment/",
        JobExperimentDetail.as_view(),
        name="job-experiment-detail",
    ),
    path(
        "<slug>/jobs/<uuid:pk>/viewers/update/",
        JobViewersUpdate.as_view(),
        name="job-viewers-update",
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
