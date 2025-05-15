from django.urls import path

from grandchallenge.discussion_forums.views import (
    ForumPostCreate,
    ForumPostDetail,
    ForumTopicCreate,
    ForumTopicDelete,
    ForumTopicDetail,
    ForumTopicListView,
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
        "topics/<slug:slug>/",
        ForumTopicDetail.as_view(),
        name="topic-detail",
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
]
