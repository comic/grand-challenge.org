from django.urls import path

from grandchallenge.archives.views import ArchiveDetail, ArchiveList

app_name = "archives"

urlpatterns = [
    path("", ArchiveList.as_view(), name="list"),
    path("<slug>/", ArchiveDetail.as_view(), name="detail"),
]
