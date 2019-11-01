from django.urls import path

from grandchallenge.workstations.views import (
    SessionCreate,
    SessionDetail,
    SessionRedirectView,
    SessionUpdate,
    WorkstationCreate,
    WorkstationDetail,
    WorkstationEditorsUpdate,
    WorkstationImageCreate,
    WorkstationImageDetail,
    WorkstationImageUpdate,
    WorkstationList,
    WorkstationUpdate,
    WorkstationUsersAutocomplete,
    WorkstationUsersUpdate,
    session_proxy,
)

app_name = "workstations"

urlpatterns = [
    path("", WorkstationList.as_view(), name="list"),
    path(
        "users-autocomplete/",
        WorkstationUsersAutocomplete.as_view(),
        name="users-autocomplete",
    ),
    path("create/", WorkstationCreate.as_view(), name="create"),
    path(
        "load/", SessionRedirectView.as_view(), name="default-session-redirect"
    ),
    path(
        "<slug>/load/",
        SessionRedirectView.as_view(),
        name="workstation-session-redirect",
    ),
    path(
        "<slug>/images/<uuid:pk>/load/",
        SessionRedirectView.as_view(),
        name="workstation-image-session-redirect",
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
        "<slug>/images/<uuid:pk>/update/",
        WorkstationImageUpdate.as_view(),
        name="image-update",
    ),
    path(
        "<slug>/sessions/create/",
        SessionCreate.as_view(),
        name="session-create",
    ),
    path(
        "<slug>/sessions/<uuid:pk>/",
        SessionDetail.as_view(),
        name="session-detail",
    ),
    path(
        "<slug>/sessions/<uuid:pk>/update/",
        SessionUpdate.as_view(),
        name="session-update",
    ),
    path(
        "<slug>/sessions/<uuid:pk>/<path:path>",
        session_proxy,
        name="session-proxy",
    ),
]
