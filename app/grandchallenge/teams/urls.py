from django.urls import path

from grandchallenge.teams.views import (
    TeamCreate,
    TeamDelete,
    TeamDetail,
    TeamList,
    TeamMemberCreate,
    TeamMemberDelete,
    TeamUpdate,
)

app_name = "teams"

urlpatterns = [
    path("all/", TeamList.as_view(), name="list"),
    path("create/", TeamCreate.as_view(), name="create"),
    path("<int:pk>/", TeamDetail.as_view(), name="detail"),
    path("<int:pk>/update/", TeamUpdate.as_view(), name="update"),
    path("<int:pk>/delete/", TeamDelete.as_view(), name="delete"),
    path(
        "<int:pk>/create-member/",
        TeamMemberCreate.as_view(),
        name="member-create",
    ),
    path(
        "member/<int:pk>/delete/",
        TeamMemberDelete.as_view(),
        name="member-delete",
    ),
]
