from django.urls import path

from grandchallenge.archives.views import (
    ArchiveCasesList,
    ArchiveCreate,
    ArchiveDetail,
    ArchiveEditorsUpdate,
    ArchiveList,
    ArchiveUpdate,
    ArchiveUploadSessionCreate,
    ArchiveUploadSessionDetail,
    ArchiveUploadSessionList,
    ArchiveUploadersUpdate,
    ArchiveUsersAutocomplete,
    ArchiveUsersUpdate,
)

app_name = "archives"

urlpatterns = [
    path("", ArchiveList.as_view(), name="list"),
    path(
        "users-autocomplete/",
        ArchiveUsersAutocomplete.as_view(),
        name="users-autocomplete",
    ),
    path("create/", ArchiveCreate.as_view(), name="create"),
    path("<slug>/", ArchiveDetail.as_view(), name="detail"),
    path("<slug>/update/", ArchiveUpdate.as_view(), name="update"),
    path(
        "<slug>/editors/update/",
        ArchiveEditorsUpdate.as_view(),
        name="editors-update",
    ),
    path(
        "<slug>/uploaders/update/",
        ArchiveUploadersUpdate.as_view(),
        name="uploaders-update",
    ),
    path(
        "<slug>/users/update/",
        ArchiveUsersUpdate.as_view(),
        name="users-update",
    ),
    path(
        "<slug>/uploads/",
        ArchiveUploadSessionList.as_view(),
        name="uploads-list",
    ),
    path(
        "<slug>/uploads/<uuid:pk>/",
        ArchiveUploadSessionDetail.as_view(),
        name="uploads-detail",
    ),
    path("<slug>/cases/", ArchiveCasesList.as_view(), name="cases-list"),
    path(
        "<slug>/cases/add/",
        ArchiveUploadSessionCreate.as_view(),
        name="cases-create",
    ),
]
