from django.urls import path

from grandchallenge.archives.views import (
    ArchiveCreate,
    ArchiveDetail,
    ArchiveEditorsUpdate,
    ArchiveItemBulkDelete,
    ArchiveItemCreateView,
    ArchiveItemDelete,
    ArchiveItemDetailView,
    ArchiveItemInterfaceCreate,
    ArchiveItemJobListView,
    ArchiveItemsList,
    ArchiveItemsToReaderStudyUpdate,
    ArchiveItemUpdate,
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
    path("<slug>/items/", ArchiveItemsList.as_view(), name="items-list"),
    path(
        "<slug>/items/<uuid:pk>/",
        ArchiveItemDetailView.as_view(),
        name="item-detail",
    ),
    path(
        "<slug>/items/<uuid:pk>/jobs",
        ArchiveItemJobListView.as_view(),
        name="item-job-list",
    ),
    path(
        "<slug>/items/create/",
        ArchiveItemCreateView.as_view(),
        name="item-create",
    ),
    path(
        "<slug>/items/delete/",
        ArchiveItemBulkDelete.as_view(),
        name="items-bulk-delete",
    ),
    path(
        "<slug>/items/new/interface/create/",
        ArchiveItemInterfaceCreate.as_view(),
        name="item-new-interface-create",
    ),
    path(
        "<slug>/items/<uuid:pk>/delete/",
        ArchiveItemDelete.as_view(),
        name="item-delete",
    ),
    path(
        "<slug>/items/<uuid:pk>/edit/",
        ArchiveItemUpdate.as_view(),
        name="item-edit",
    ),
    path(
        "<slug>/items/<uuid:pk>/interface/create/",
        ArchiveItemInterfaceCreate.as_view(),
        name="item-interface-create",
    ),
    path(
        "<slug>/cases/add/",
        ArchiveUploadSessionCreate.as_view(),
        name="cases-create",
    ),
    path(
        "<slug>/items/reader-study/update/",
        ArchiveItemsToReaderStudyUpdate.as_view(),
        name="items-reader-study-update",
    ),
]
