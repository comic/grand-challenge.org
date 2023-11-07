from django.urls import path, re_path

from grandchallenge.direct_messages.views import (
    ConversationCreate,
    ConversationDetail,
)

app_name = "direct_messages"

urlpatterns = [
    re_path(
        r"^create/(?P<username>[\@\.\+\w-]+)/$",
        ConversationCreate.as_view(),
        name="conversation-create",
    ),
    path(
        "<uuid:pk>/", ConversationDetail.as_view(), name="conversation-detail"
    ),
]
