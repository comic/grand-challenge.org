from django.urls import path, re_path

from grandchallenge.groups.views import UserAutocomplete
from grandchallenge.profiles.views import (
    UserProfileDetail,
    profile,
    profile_edit,
)

urlpatterns = [
    path(
        "user-autocomplete/",
        UserAutocomplete.as_view(),
        name="users-autocomplete",
    ),
    path("profile/", profile, name="profile-detail-redirect"),
    re_path(
        r"^(?P<username>[\@\.\+\w-]+)/$",
        UserProfileDetail.as_view(),
        name="profile-detail",
    ),
    re_path(
        r"^(?P<username>[\@\.\+\w-]+)/edit/$",
        profile_edit,
        name="profile-update",
    ),
]
