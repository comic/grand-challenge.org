from django.urls import path

from grandchallenge.publications.views import (
    PublicationCreate,
    PublicationList,
)

app_name = "publications"

urlpatterns = [
    path("", PublicationList.as_view(), name="list"),
    path("create/", PublicationCreate.as_view(), name="create",),
]
