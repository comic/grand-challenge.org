from django.urls import path

from grandchallenge.admins.views import AdminsList, AdminsUpdate
from grandchallenge.groups.views import UserAutocomplete

app_name = "admins"

urlpatterns = [
    path("all/", AdminsList.as_view(), name="list"),
    path("update/", AdminsUpdate.as_view(), name="update"),
    path(
        "users-autocomplete/",
        UserAutocomplete.as_view(),
        name="users-autocomplete",
    ),
]
