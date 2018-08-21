from django.conf.urls import url

from grandchallenge.teams.views import (
    TeamList,
    TeamDetail,
    TeamUpdate,
    TeamCreate,
    TeamMemberCreate,
    TeamMemberDelete,
    TeamDelete,
)

app_name = "teams"

urlpatterns = [
    url(r"^$", TeamList.as_view(), name="list"),
    url(r"^t/create/$", TeamCreate.as_view(), name="create"),
    url(r"^t/(?P<pk>[0-9]+)/$", TeamDetail.as_view(), name="detail"),
    url(r"^t/(?P<pk>[0-9]+)/update/$", TeamUpdate.as_view(), name="update"),
    url(r"^t/(?P<pk>[0-9]+)/delete/$", TeamDelete.as_view(), name="delete"),
    url(
        r"^t/(?P<pk>[0-9]+)/create-member/$",
        TeamMemberCreate.as_view(),
        name="member-create",
    ),
    url(
        r"^m/(?P<pk>[0-9]+)/delete/$",
        TeamMemberDelete.as_view(),
        name="member-delete",
    ),
]
