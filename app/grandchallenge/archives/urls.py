from django.urls import path

from grandchallenge.archives.views import (
    ArchiveCasesList,
    ArchiveCasesToReaderStudyUpdate,
    ArchiveCreate,
    ArchiveDetail,
    ArchiveEditArchiveItem,
    ArchiveEditorsUpdate,
    ArchiveItemsList,
    ArchiveList,
    ArchivePermissionRequestCreate,
    ArchivePermissionRequestList,
    ArchivePermissionRequestUpdate,
    ArchiveUpdate,
    ArchiveUploadSessionCreate,
    ArchiveUploadersUpdate,
    ArchiveUsersUpdate,
)

app_name = "archives"

urlpatterns = [
    path("", ArchiveList.as_view(), name="list"),
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
        "<slug>/permission-requests/",
        ArchivePermissionRequestList.as_view(),
        name="permission-request-list",
    ),
    path(
        "<slug>/permission-requests/create/",
        ArchivePermissionRequestCreate.as_view(),
        name="permission-request-create",
    ),
    path(
        "<slug>/permission-requests/<int:pk>/update/",
        ArchivePermissionRequestUpdate.as_view(),
        name="permission-request-update",
    ),
    path("<slug>/cases/", ArchiveCasesList.as_view(), name="cases-list"),
    path("<slug>/items/", ArchiveItemsList.as_view(), name="items-list"),
    path(
        "<slug>/cases/add/",
        ArchiveUploadSessionCreate.as_view(),
        name="cases-create",
    ),
    path(
        "<slug>/items/<id>/edit",
        ArchiveEditArchiveItem.as_view(),
        name="item-edit",
    ),
    path(
        "<slug>/cases/reader-study/update/",
        ArchiveCasesToReaderStudyUpdate.as_view(),
        name="cases-reader-study-update",
    ),
]
