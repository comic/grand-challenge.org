from django.urls import path

from grandchallenge.challenges.views import (
    ChallengeCostOverview,
    ChallengeList,
    ChallengeRequestBudgetUpdate,
    ChallengeRequestCreate,
    ChallengeRequestDetail,
    ChallengeRequestList,
    ChallengeRequestStatusUpdate,
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
    path("requests/", ChallengeRequestList.as_view(), name="requests-list"),
    path(
        "requests/create/",
        ChallengeRequestCreate.as_view(),
        name="requests-create",
    ),
    path(
        "requests/<pk>/",
        ChallengeRequestDetail.as_view(),
        name="requests-detail",
    ),
    path(
        "requests/<pk>/update/status/",
        ChallengeRequestStatusUpdate.as_view(),
        name="requests-status-update",
    ),
    path(
        "requests/<pk>/update/budget/",
        ChallengeRequestBudgetUpdate.as_view(),
        name="requests-budget-update",
    ),
    path(
        "cost-overview", ChallengeCostOverview.as_view(), name="cost-overview"
    ),
]
