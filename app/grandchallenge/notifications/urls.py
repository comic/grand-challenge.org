from django.urls import path

from grandchallenge.notifications.views import (
    FollowDelete,
    FollowList,
    NotificationList,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationList.as_view(), name="list"),
    path("subscriptions/", FollowList.as_view(), name="follow-list"),
    path(
        "subscriptions/<int:pk>/delete/",
        FollowDelete.as_view(),
        name="follow-delete",
    ),
]
