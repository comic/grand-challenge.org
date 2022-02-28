from django.urls import path

from grandchallenge.challenges.views import (
    ChallengeCreate,
    ChallengeList,
    ChallengeRequestCreate,
    ChallengeRequestDetail,
    ChallengeRequestList,
    ChallengeRequestUpdate,
    CombinedChallengeList,
    ExternalChallengeCreate,
    ExternalChallengeList,
    ExternalChallengeUpdate,
    UsersChallengeList,
)

app_name = "challenges"

urlpatterns = [
    path("", ChallengeList.as_view(), name="list"),
    path(
        "all-challenges/",
        CombinedChallengeList.as_view(),
        name="combined-list",
    ),
    path("my-challenges/", UsersChallengeList.as_view(), name="users-list"),
    path("create/", ChallengeCreate.as_view(), name="create"),
    path("external/", ExternalChallengeList.as_view(), name="external-list"),
    path(
        "external/create/",
        ExternalChallengeCreate.as_view(),
        name="external-create",
    ),
    path(
        "external/<slug:short_name>/update/",
        ExternalChallengeUpdate.as_view(),
        name="external-update",
    ),
    path("request/", ChallengeRequestCreate.as_view(), name="request"),
    path("request-list/", ChallengeRequestList.as_view(), name="request-list"),
    path(
        "request/<pk>/",
        ChallengeRequestDetail.as_view(),
        name="request-detail",
    ),
    path(
        "request/<pk>/update/",
        ChallengeRequestUpdate.as_view(),
        name="request-update",
    ),
]
