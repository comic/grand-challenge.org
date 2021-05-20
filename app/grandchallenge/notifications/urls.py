from django.urls import path

from grandchallenge.notifications.views import (
    NotificationList,
    NotificationUpdate,
    SubscriptionListView,
    SubscriptionUpdate,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationList.as_view(), name="list"),
    path("<int:pk>/update", NotificationUpdate.as_view(), name="update"),
    path(
        "subscriptions/",
        SubscriptionListView.as_view(
            template_name="notifications/follow_list.html"
        ),
        name="subscriptions-list",
    ),
    path(
        "subscriptions/<int:pk>/update",
        SubscriptionUpdate.as_view(),
        name="subscription-update",
    ),
]
