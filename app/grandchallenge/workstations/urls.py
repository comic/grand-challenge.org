from django.urls import path

from grandchallenge.workstations.views import (
    DebugSessionCreate,
    SessionCreate,
    WorkstationCreate,
    WorkstationDetail,
    WorkstationEditorsUpdate,
    WorkstationImageCreate,
    WorkstationImageDetail,
    WorkstationImageImportStatusDetail,
    WorkstationImageMove,
    WorkstationImageUpdate,
    WorkstationList,
    WorkstationUpdate,
    WorkstationUsersUpdate,
)

app_name = "workstations"

urlpatterns = [
    path("", WorkstationList.as_view(), name="list"),
    path("create/", WorkstationCreate.as_view(), name="create"),
    path(
        "sessions/create/",
        SessionCreate.as_view(),
        name="default-session-create",
    ),
    path(
        "<slug>/sessions/create/",
        SessionCreate.as_view(),
        name="workstation-session-create",
    ),
    path(
        "<slug>/sessions/create/<path:workstation_path>/",
        SessionCreate.as_view(),
        name="workstation-session-create-nested",
    ),
    path(
        "<slug>/sessions/debug/create/",
        DebugSessionCreate.as_view(),
        name="workstation-debug-session-create",
    ),
    path(
        "<slug>/sessions/debug/create/<path:workstation_path>/",
        DebugSessionCreate.as_view(),
        name="workstation-debug-session-create-nested",
    ),
    path(
        "<slug>/editors/update/",
        WorkstationEditorsUpdate.as_view(),
        name="editors-update",
    ),
    path(
        "<slug>/users/update/",
        WorkstationUsersUpdate.as_view(),
        name="users-update",
    ),
    path("<slug>/", WorkstationDetail.as_view(), name="detail"),
    path("<slug>/update/", WorkstationUpdate.as_view(), name="update"),
    path(
        "<slug>/images/create/",
        WorkstationImageCreate.as_view(),
        name="image-create",
    ),
    path(
        "<slug>/images/<uuid:pk>/",
        WorkstationImageDetail.as_view(),
        name="image-detail",
    ),
    path(
        "<slug>/images/<uuid:pk>/import-status/",
        WorkstationImageImportStatusDetail.as_view(),
        name="image-import-status-detail",
    ),
    path(
        "<slug>/images/<uuid:pk>/update/",
        WorkstationImageUpdate.as_view(),
        name="image-update",
    ),
    path(
        "<slug>/images/<uuid:pk>/move/",
        WorkstationImageMove.as_view(),
        name="image-move",
    ),
]
