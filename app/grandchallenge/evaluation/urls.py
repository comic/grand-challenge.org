from django.urls import path
from django.views.generic import RedirectView

from grandchallenge.evaluation.views import (
    EvaluationDetail,
    EvaluationList,
    EvaluationUpdate,
    LeaderboardDetail,
    LegacySubmissionCreate,
    MethodCreate,
    MethodDetail,
    MethodList,
    PhaseUpdate,
    SubmissionCreate,
    SubmissionDetail,
    SubmissionList,
)

app_name = "evaluation"

urlpatterns = [
    path(
        "<slug>/leaderboard/", LeaderboardDetail.as_view(), name="leaderboard"
    ),
    path("<slug>/update/", PhaseUpdate.as_view(), name="phase-update"),
    path(
        "<slug>/submissions/create/",
        SubmissionCreate.as_view(),
        name="submission-create",
    ),
    path(
        "<slug>/submissions/create-legacy/",
        LegacySubmissionCreate.as_view(),
        name="submission-create-legacy",
    ),
    # path("config/", PhaseUpdate.as_view(), name="config-update"),
    path("methods/", MethodList.as_view(), name="method-list"),
    path("methods/create/", MethodCreate.as_view(), name="method-create"),
    path("methods/<uuid:pk>/", MethodDetail.as_view(), name="method-detail"),
    path("submissions/", SubmissionList.as_view(), name="submission-list"),
    # path(
    #    "submissions/create/",
    #    SubmissionCreate.as_view(),
    #    name="submission-create",
    # ),
    # path(
    #    "submissions/create-legacy/",
    #    LegacySubmissionCreate.as_view(),
    #    name="submission-create-legacy",
    # ),
    path(
        "submissions/<uuid:pk>/",
        SubmissionDetail.as_view(),
        name="submission-detail",
    ),
    # path("leaderboard/", LeaderboardDetail.as_view(), name="leaderboard",),
    path("", EvaluationList.as_view(), name="list"),
    path("<uuid:pk>/", EvaluationDetail.as_view(), name="detail"),
    path("<uuid:pk>/update/", EvaluationUpdate.as_view(), name="update"),
    path(
        "results/", RedirectView.as_view(url="../leaderboard/", permanent=True)
    ),
]
