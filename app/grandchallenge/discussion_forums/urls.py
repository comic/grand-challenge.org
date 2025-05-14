from django.urls import path

from grandchallenge.discussion_forums.views import (
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
]
