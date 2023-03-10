from django.urls import path

from grandchallenge.challenges.views import (
    ChallengeCostCalculation,
    ChallengeCostOverview,
    ChallengeCostsPerPhaseView,
    ChallengeCostsPerYearView,
    ChallengeCostsRow,
    ChallengeList,
    ChallengeRequestBudgetUpdate,
    ChallengeRequestCreate,
    ChallengeRequestDetail,
    ChallengeRequestList,
    ChallengeRequestStatusUpdate,
    UsersChallengeList,
    YearCostsRow,
)

app_name = "challenges"

urlpatterns = [
    path("", ChallengeList.as_view(), name="list"),
    path("my-challenges/", UsersChallengeList.as_view(), name="users-list"),
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
    path(
        "costs/<pk>/costs-per-phase/",
        ChallengeCostsPerPhaseView.as_view(),
        name="costs-per-phase",
    ),
    path(
        "costs/<pk>/cost-row/",
        ChallengeCostsRow.as_view(),
        name="challenge-cost-row",
    ),
    path(
        "costs/costs-per-year/",
        ChallengeCostsPerYearView.as_view(),
        name="costs-per-year",
    ),
    path(
        "costs/year-row/",
        YearCostsRow.as_view(),
        name="year-cost-row",
    ),
]
