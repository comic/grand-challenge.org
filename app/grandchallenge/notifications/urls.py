from django.urls import path

from grandchallenge.notifications.views import (
    NotificationList,
    NotificationUpdate,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationList.as_view(), name="list"),
    path("<int:pk>/update", NotificationUpdate.as_view(), name="update"),
]
