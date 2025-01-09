from django.urls import path

from grandchallenge.emails.views import (
    EmailBodyUpdate,
    EmailCreate,
    EmailDetail,
    EmailList,
    EmailMetadataUpdate,
)

app_name = "emails"

urlpatterns = [
    path("", EmailList.as_view(), name="list"),
    path("create/", EmailCreate.as_view(), name="create"),
    path("<int:pk>/", EmailDetail.as_view(), name="detail"),
    path(
        "<int:pk>/metadata-update/",
        EmailMetadataUpdate.as_view(),
        name="metadata-update",
    ),
    path(
        "<int:pk>/body-update/", EmailBodyUpdate.as_view(), name="body-update"
    ),
]
