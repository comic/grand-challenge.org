from django.urls import path, re_path

from grandchallenge.direct_messages.views import (
    ConversationCreate,
    ConversationDetail,
    ConversationList,
    ConversationMarkRead,
    ConversationSelectDetail,
    DirectMessageCreate,
    DirectMessageDelete,
    DirectMessageReportSpam,
    MuteCreate,
    MuteDelete,
)

app_name = "direct_messages"


urlpatterns = [
    path("", ConversationList.as_view(), name="conversation-list"),
    re_path(
        r"^create/(?P<username>[\@\.\+\w-]+)/$",
        ConversationCreate.as_view(),
        name="conversation-create",
    ),
    re_path(
        r"^mute/(?P<username>[\@\.\+\w-]+)/$",
        MuteCreate.as_view(),
        name="mute-create",
    ),
    path(
        "mute/<uuid:pk>/delete/",
        MuteDelete.as_view(),
        name="mute-delete",
    ),
    path(
        "<uuid:pk>/", ConversationDetail.as_view(), name="conversation-detail"
    ),
    path(
        "<uuid:pk>/mark-read/",
        ConversationMarkRead.as_view(),
        name="conversation-mark-read",
    ),
    path(
        "<uuid:pk>/select/",
        ConversationSelectDetail.as_view(),
        name="conversation-select-detail",
    ),
    path(
        "<uuid:pk>/create/",
        DirectMessageCreate.as_view(),
        name="direct-message-create",
    ),
    path(
        "<uuid:conversation_pk>/messages/<uuid:pk>/delete/",
        DirectMessageDelete.as_view(),
        name="direct-message-delete",
    ),
    path(
        "<uuid:conversation_pk>/messages/<uuid:pk>/report-spam/",
        DirectMessageReportSpam.as_view(),
        name="direct-message-report-spam",
    ),
]
