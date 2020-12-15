from django.urls import path

from grandchallenge.organizations.views import (
    OrganizationDetail,
    OrganizationEditorsUpdate,
    OrganizationList,
    OrganizationMembersUpdate,
    OrganizationUserAutocomplete,
)

app_name = "organizations"

urlpatterns = [
    path("", OrganizationList.as_view(), name="list"),
    path(
        "users-autocomplete/",
        OrganizationUserAutocomplete.as_view(),
        name="users-autocomplete",
    ),
    path("<slug>/", OrganizationDetail.as_view(), name="detail"),
    path(
        "<slug>/editors/update/",
        OrganizationEditorsUpdate.as_view(),
        name="editors-update",
    ),
    path(
        "<slug>/members/update/",
        OrganizationMembersUpdate.as_view(),
        name="members-update",
    ),
]
