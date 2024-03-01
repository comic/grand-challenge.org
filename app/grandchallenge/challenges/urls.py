from django.urls import path

from grandchallenge.challenges.views import (
    ChallengeCostCalculation,
    ChallengeCostOverview,
    ChallengeList,
    ChallengeRequestBudgetUpdate,
    ChallengeRequestCreate,
    ChallengeRequestDetail,
    ChallengeRequestList,
    ChallengeRequestStatusUpdate,
    UsersChallengeList,
)
from grandchallenge.evaluation.views import ConfigureAlgorithmPhasesView

app_name = "challenges"

urlpatterns = [
    path("", ChallengeList.as_view(), name="list"),
    path("my-challenges/", UsersChallengeList.as_view(), name="users-list"),
    path(
        "configure-algorithm-phases/",
        ConfigureAlgorithmPhasesView.as_view(),
        name="configure-algorithm-phases",
    ),
    path("requests/", ChallengeRequestList.as_view(), name="requests-list"),
    path(
        "requests/create/",
        ChallengeRequestCreate.as_view(),
        name="requests-create",
    ),
    path(
        "requests/cost-calculation/",
        ChallengeCostCalculation.as_view(),
        name="requests-cost-calculation",
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
        "costs/",
        ChallengeCostOverview.as_view(),
        name="cost-overview",
    ),
]
