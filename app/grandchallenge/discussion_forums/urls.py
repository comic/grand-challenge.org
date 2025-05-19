from django.urls import path

from grandchallenge.discussion_forums.views import (
    ForumPostCreate,
    ForumPostDelete,
    ForumPostDetail,
    ForumPostUpdate,
    ForumTopicCreate,
    ForumTopicDelete,
    ForumTopicDetail,
    ForumTopicListView,
    ForumTopicLockUpdate,
    MyForumPosts,
)

app_name = "discussion_forums"


urlpatterns = [
    path("", ForumTopicListView.as_view(), name="topic-list"),
    path("my-posts/", MyForumPosts.as_view(), name="my-posts"),
    path(
        "topics/create/",
        ForumTopicCreate.as_view(),
        name="topic-create",
    ),
    path(
        "topics/<slug:slug>/",
        ForumTopicDetail.as_view(),
        name="topic-detail",
    ),
    path(
        "topics/<slug:slug>/lock/",
        ForumTopicLockUpdate.as_view(),
        name="topic-lock-update",
    ),
    path(
        "topics/<slug:slug>/delete/",
        ForumTopicDelete.as_view(),
        name="topic-delete",
    ),
    path(
        "topics/<slug:slug>/posts/create/",
        ForumPostCreate.as_view(),
        name="post-create",
    ),
    path(
        "topics/<slug:slug>/posts/<uuid:pk>/",
        ForumPostDetail.as_view(),
        name="post-detail",
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
