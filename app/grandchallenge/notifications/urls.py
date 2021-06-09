from django.urls import path

from grandchallenge.notifications.views import (
    NotificationList,
    # NotificationUpdate,
    SubscriptionCreate,
    SubscriptionDelete,
    SubscriptionListView,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationList.as_view(), name="list"),
    # path("<int:pk>/update", NotificationUpdate.as_view(), name="update"),
    path(
        "subscriptions/",
        SubscriptionListView.as_view(
            template_name="notifications/subscription_list.html"
        ),
        name="subscriptions-list",
    ),
    path(
        "subscriptions/<int:pk>/update",
        SubscriptionDelete.as_view(),
        name="subscription-delete",
    ),
    path(
        "subscriptions/create",
        SubscriptionCreate.as_view(),
        name="subscription-create",
    ),
]
