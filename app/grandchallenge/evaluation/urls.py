from django.urls import path

from grandchallenge.evaluation.views import (
    EvaluationAdminList,
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
    # UUID should be matched before slugs
    path("<uuid:pk>/update/", EvaluationUpdate.as_view(), name="update"),
    path("phase/create/", PhaseCreate.as_view(), name="phase-create"),
    path("submissions/", SubmissionList.as_view(), name="submission-list"),
    path("<slug>/", EvaluationList.as_view(), name="list"),
    path(
        "<slug>/admin/",
        EvaluationAdminList.as_view(),
        name="evaluation-admin-list",
    ),
    path(
        "<slug>/algorithms/create/",
        PhaseAlgorithmCreate.as_view(),
        name="phase-algorithm-create",
    ),
    path(
        "<slug>/leaderboard/", LeaderboardDetail.as_view(), name="leaderboard"
    ),
    path("<slug>/methods/", MethodList.as_view(), name="method-list"),
    path(
        "<slug>/methods/create/", MethodCreate.as_view(), name="method-create"
    ),
    path(
        "<slug>/methods/<uuid:pk>/",
        MethodDetail.as_view(),
        name="method-detail",
    ),
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
    path(
        "<slug>/submissions/<uuid:pk>/",
        SubmissionDetail.as_view(),
        name="submission-detail",
    ),
    path("<slug>/update/", PhaseUpdate.as_view(), name="phase-update"),
    path("results/", LeaderboardRedirect.as_view()),
    path("leaderboard/", LeaderboardRedirect.as_view()),
]
