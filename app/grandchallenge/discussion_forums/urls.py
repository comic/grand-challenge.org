from django.urls import path

from grandchallenge.discussion_forums.views import TopicCreate, TopicDetail

app_name = "discussion_forums"


urlpatterns = [
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
]
