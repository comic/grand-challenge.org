from django.urls import path

from grandchallenge.evaluation.views import (
    EvaluationDetail,
    EvaluationList,
    EvaluationUpdate,
    LeaderboardDetail,
    LeaderboardRedirect,
    LegacySubmissionCreate,
    MethodCreate,
    MethodDetail,
    MethodList,
    PhaseAlgorithmCreate,
    PhaseCreate,
    PhaseUpdate,
    SubmissionCreate,
    SubmissionDetail,
    SubmissionList,
)

app_name = "evaluation"

urlpatterns = [
    path("<uuid:pk>/", EvaluationDetail.as_view(), name="detail"),
    path("<slug>/", EvaluationList.as_view(), name="list"),
    # UUID should be matched before slugs
    path("<uuid:pk>/update/", EvaluationUpdate.as_view(), name="update"),
    path("phase/create/", PhaseCreate.as_view(), name="phase-create"),
    path(
        "<slug>/algorithms/create/",
        PhaseAlgorithmCreate.as_view(),
        name="phase-algorithm-create",
    ),
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
    path("methods/<uuid:pk>/", MethodDetail.as_view(), name="method-detail"),
    path("methods/<slug>/", MethodList.as_view(), name="method-list"),
    path(
        "methods/<slug>/create/", MethodCreate.as_view(), name="method-create"
    ),
    path("submissions/", SubmissionList.as_view(), name="submission-list"),
    path(
        "submissions/<uuid:pk>/",
        SubmissionDetail.as_view(),
        name="submission-detail",
    ),
    path("results/", LeaderboardRedirect.as_view()),
    path("leaderboard/", LeaderboardRedirect.as_view()),
]
