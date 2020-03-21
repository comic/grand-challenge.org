from django.urls import path

from grandchallenge.archives.views import (
    ArchiveCreate,
    ArchiveDetail,
    ArchiveEditorsUpdate,
    ArchiveList,
    ArchiveUpdate,
    ArchiveUploadSessionCreate,
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
        "<slug>/users/update/",
        ArchiveUsersUpdate.as_view(),
        name="users-update",
    ),
    path(
        "<slug>/cases/add/",
        ArchiveUploadSessionCreate.as_view(),
        name="add-cases",
    ),
]
