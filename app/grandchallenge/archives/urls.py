from django.urls import path

from grandchallenge.archives.views import (
    ArchiveCreate,
    ArchiveDetail,
    ArchiveList,
)

app_name = "archives"

urlpatterns = [
    path("", ArchiveList.as_view(), name="list"),
    path("create/", ArchiveCreate.as_view(), name="create"),
    path("<slug>/", ArchiveDetail.as_view(), name="detail"),
]
