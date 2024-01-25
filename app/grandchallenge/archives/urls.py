from django.urls import path

from grandchallenge.archives.views import (
    ArchiveCasesList,
    ArchiveCreate,
    ArchiveDetail,
    ArchiveEditArchiveItem,
    ArchiveEditorsUpdate,
    ArchiveItemDeleteView,
    ArchiveItemsList,
    ArchiveItemsToReaderStudyUpdate,
    ArchiveList,
    ArchivePermissionRequestCreate,
    ArchivePermissionRequestList,
    ArchivePermissionRequestUpdate,
    ArchiveUpdate,
    ArchiveUploadersUpdate,
    ArchiveUploadSessionCreate,
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
        "<slug>/items/<uuid:pk>/delete/",
        ArchiveItemDeleteView.as_view(),
        name="item-delete",
    ),
    path(
        "<slug>/cases/add/",
        ArchiveUploadSessionCreate.as_view(),
        name="cases-create",
    ),
    path(
        "<slug:archive_slug>/items/<uuid:pk>/edit/<slug:interface_slug>/",
        ArchiveEditArchiveItem.as_view(),
        name="item-edit",
    ),
    path(
        "<slug>/items/reader-study/update/",
        ArchiveItemsToReaderStudyUpdate.as_view(),
        name="items-reader-study-update",
    ),
]
