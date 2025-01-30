from django.urls import path

from grandchallenge.algorithms.views import (
    AlgorithmCreate,
    AlgorithmDescriptionUpdate,
    AlgorithmDetail,
    AlgorithmImageActivate,
    AlgorithmImageBuildStatusDetail,
    AlgorithmImageCreate,
    AlgorithmImageDetail,
    AlgorithmImageImportStatusDetail,
    AlgorithmImageTemplate,
    AlgorithmImageUpdate,
    AlgorithmImportView,
    AlgorithmList,
    AlgorithmModelCreate,
    AlgorithmModelDetail,
    AlgorithmModelImportStatusDetail,
    AlgorithmModelUpdate,
    AlgorithmModelVersionControl,
    AlgorithmPermissionRequestCreate,
    AlgorithmPermissionRequestList,
    AlgorithmPermissionRequestUpdate,
    AlgorithmPublishView,
    AlgorithmRepositoryUpdate,
    AlgorithmStatistics,
    AlgorithmUpdate,
    DisplaySetFromJobCreate,
    EditorsUpdate,
    JobCreate,
    JobDetail,
    JobProgressDetail,
    JobsList,
    JobStatusDetail,
    JobUpdate,
    JobViewersUpdate,
    UsersUpdate,
)

app_name = "algorithms"

urlpatterns = [
    path("", AlgorithmList.as_view(), name="list"),
    path("create/", AlgorithmCreate.as_view(), name="create"),
    path("import/", AlgorithmImportView.as_view(), name="import"),
    path("<slug>/", AlgorithmDetail.as_view(), name="detail"),
    path(
        "<slug>/statistics/", AlgorithmStatistics.as_view(), name="statistics"
    ),
    path("<slug>/update/", AlgorithmUpdate.as_view(), name="update"),
    path("<slug>/publish/", AlgorithmPublishView.as_view(), name="publish"),
    path(
        "<slug>/description-update/",
        AlgorithmDescriptionUpdate.as_view(),
        name="description-update",
    ),
    path(
        "<slug>/repository/",
        AlgorithmRepositoryUpdate.as_view(),
        name="repository-update",
    ),
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
        "<slug>/images/<uuid:pk>/import-status/",
        AlgorithmImageImportStatusDetail.as_view(),
        name="image-import-status-detail",
    ),
    path(
        "<slug>/images/<uuid:pk>/build-status/",
        AlgorithmImageBuildStatusDetail.as_view(),
        name="image-build-status-detail",
    ),
    path(
        "<slug>/images/activate/",
        AlgorithmImageActivate.as_view(),
        name="image-activate",
    ),
    path(
        "<slug>/images/template/",
        AlgorithmImageTemplate.as_view(),
        name="image-template",
    ),
    path(
        "<slug>/images/<uuid:pk>/update/",
        AlgorithmImageUpdate.as_view(),
        name="image-update",
    ),
    path(
        "<slug>/models/<uuid:pk>/",
        AlgorithmModelDetail.as_view(),
        name="model-detail",
    ),
    path(
        "<slug>/models/<uuid:pk>/import-status/",
        AlgorithmModelImportStatusDetail.as_view(),
        name="model-import-status-detail",
    ),
    path(
        "<slug>/models/create/",
        AlgorithmModelCreate.as_view(),
        name="model-create",
    ),
    path(
        "<slug>/models/activate/",
        AlgorithmModelVersionControl.as_view(activate=True),
        name="model-activate",
    ),
    path(
        "<slug>/models/deactivate/",
        AlgorithmModelVersionControl.as_view(activate=False),
        name="model-deactivate",
    ),
    path(
        "<slug>/models/<uuid:pk>/update/",
        AlgorithmModelUpdate.as_view(),
        name="model-update",
    ),
    path("<slug>/jobs/", JobsList.as_view(), name="job-list"),
    path("<slug>/jobs/create/", JobCreate.as_view(), name="job-create"),
    path("<slug>/jobs/<uuid:pk>/", JobDetail.as_view(), name="job-detail"),
    path(
        "<slug>/jobs/<uuid:pk>/status/",
        JobStatusDetail.as_view(),
        name="job-status-detail",
    ),
    path(
        "<slug>/jobs/<uuid:pk>/update/", JobUpdate.as_view(), name="job-update"
    ),
    path(
        "<slug>/jobs/<uuid:pk>/display-set/create/",
        DisplaySetFromJobCreate.as_view(),
        name="display-set-from-job-create",
    ),
    path(
        "<slug>/jobs/<uuid:pk>/progress/",
        JobProgressDetail.as_view(),
        name="job-progress-detail",
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
