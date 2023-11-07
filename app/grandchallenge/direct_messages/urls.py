from django.urls import path, re_path

from grandchallenge.direct_messages.views import (
    ConversationCreate,
    ConversationDetail,
    ConversationList,
    DirectMessageCreate,
)

app_name = "direct_messages"

urlpatterns = [
    path("", ConversationList.as_view(), name="conversation-list"),
    re_path(
        r"^create/(?P<username>[\@\.\+\w-]+)/$",
        ConversationCreate.as_view(),
        name="conversation-create",
    ),
    path(
        "<uuid:pk>/", ConversationDetail.as_view(), name="conversation-detail"
    ),
    path(
        "<uuid:pk>/create/",
        DirectMessageCreate.as_view(),
        name="direct-message-create",
    ),
]
