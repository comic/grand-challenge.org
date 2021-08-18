from django.urls import path

from grandchallenge.blogs.views import (
    AuthorsUpdate,
    PostCreate,
    PostDetail,
    PostList,
    PostUpdate,
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
    path("<slug>/update/", PostUpdate.as_view(), name="update"),
]
