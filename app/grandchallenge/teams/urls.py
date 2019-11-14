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
    path("", TeamList.as_view(), name="list"),
    path("t/create/", TeamCreate.as_view(), name="create"),
    path("t/<int:pk>/", TeamDetail.as_view(), name="detail"),
    path("t/<int:pk>/update/", TeamUpdate.as_view(), name="update"),
    path("t/<int:pk>/delete/", TeamDelete.as_view(), name="delete"),
    path(
        "t/<int:pk>/create-member/",
        TeamMemberCreate.as_view(),
        name="member-create",
    ),
    path(
        "m/<int:pk>/delete/", TeamMemberDelete.as_view(), name="member-delete"
    ),
]
