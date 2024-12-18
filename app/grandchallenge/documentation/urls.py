from django.urls import path

from grandchallenge.documentation.views import (
    DocPageContentUpdate,
    DocPageCreate,
    DocPageDetail,
    DocPageList,
    DocPageMetadataUpdate,
    DocumentationHome,
)

app_name = "documentation"


urlpatterns = [
    path("", DocumentationHome.as_view(), name="home"),
    path("overview/", DocPageList.as_view(), name="list"),
    path("create/", DocPageCreate.as_view(), name="create"),
    path("<slug:slug>/", DocPageDetail.as_view(), name="detail"),
    path(
        "<slug:slug>/content-update/",
        DocPageContentUpdate.as_view(),
        name="content-update",
    ),
    path(
        "<slug:slug>/metadata-update/",
        DocPageMetadataUpdate.as_view(),
        name="metadata-update",
    ),
]
