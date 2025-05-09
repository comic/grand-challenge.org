from django.urls import path

from grandchallenge.discussion_forums.views import (
    TopicCreate,
    TopicDelete,
    TopicDetail,
    TopicListView,
)

app_name = "discussion_forums"


urlpatterns = [
    path("", TopicListView.as_view(), name="topic-list"),
    path(
        "topics/create/",
        TopicCreate.as_view(),
        name="topic-create",
    ),
    path(
        "topics/<uuid:pk>/",
        TopicDetail.as_view(),
        name="topic-detail",
    ),
    path(
        "topics/<uuid:pk>/delete/",
        TopicDelete.as_view(),
        name="topic-delete",
    ),
]
