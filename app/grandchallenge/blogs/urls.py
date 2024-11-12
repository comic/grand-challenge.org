from django.urls import path

from grandchallenge.blogs.views import (
    AuthorsUpdate,
    PostContentUpdate,
    PostCreate,
    PostDetail,
    PostList,
    PostMetaDataUpdate,
)

app_name = "blogs"

urlpatterns = [
    path("", PostList.as_view(), name="list"),
    path("create/", PostCreate.as_view(), name="create"),
    path(
        "<slug>/authors/update/",
        AuthorsUpdate.as_view(),
        name="authors-update",
    ),
    path("<slug>/", PostDetail.as_view(), name="detail"),
    path(
        "<slug>/metadata-update/",
        PostMetaDataUpdate.as_view(),
        name="metadata-update",
    ),
    path(
        "<slug>/content-update/",
        PostContentUpdate.as_view(),
        name="content-update",
    ),
]
