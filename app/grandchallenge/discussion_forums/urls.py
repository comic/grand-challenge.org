from django.urls import path

from grandchallenge.discussion_forums.views import (
    ForumPostCreate,
    ForumPostDelete,
    ForumPostUpdate,
    ForumTopicCreate,
    ForumTopicDelete,
    ForumTopicListView,
    ForumTopicPostList,
)

app_name = "discussion_forums"


urlpatterns = [
    path("", ForumTopicListView.as_view(), name="topic-list"),
    path(
        "topics/create/",
        ForumTopicCreate.as_view(),
        name="topic-create",
    ),
    path(
        "topics/<slug:slug>/delete/",
        ForumTopicDelete.as_view(),
        name="topic-delete",
    ),
    path(
        "topics/<slug:slug>/",
        ForumTopicPostList.as_view(),
        name="topic-post-list",
    ),
    path(
        "topics/<slug:slug>/posts/create/",
        ForumPostCreate.as_view(),
        name="post-create",
    ),
    path(
        "topics/<slug:slug>/posts/<uuid:pk>/delete/",
        ForumPostDelete.as_view(),
        name="post-delete",
    ),
    path(
        "topics/<slug:slug>/posts/<uuid:pk>/update/",
        ForumPostUpdate.as_view(),
        name="post-update",
    ),
]
