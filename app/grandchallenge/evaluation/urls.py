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
    ObservableDetail,
    PhaseCreate,
    PhaseUpdate,
    SubmissionCreate,
    SubmissionDetail,
    SubmissionList,
)

app_name = "evaluation"

urlpatterns = [
    path("", EvaluationList.as_view(), name="list"),
    path("<uuid:pk>/", EvaluationDetail.as_view(), name="detail"),
    # UUID should be matched before slugs
    path("<uuid:pk>/update/", EvaluationUpdate.as_view(), name="update"),
    path("phase/create/", PhaseCreate.as_view(), name="phase-create"),
    path(
        "<slug>/leaderboard/", LeaderboardDetail.as_view(), name="leaderboard"
    ),
    path(
        "<slug>/observable/<slug:kind>/",
        ObservableDetail.as_view(),
        name="observable-detail",
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
    path("methods/", MethodList.as_view(), name="method-list"),
    path("methods/create/", MethodCreate.as_view(), name="method-create"),
    path("methods/<uuid:pk>/", MethodDetail.as_view(), name="method-detail"),
    path("submissions/", SubmissionList.as_view(), name="submission-list"),
    path(
        "submissions/<uuid:pk>/",
        SubmissionDetail.as_view(),
        name="submission-detail",
    ),
    path("results/", LeaderboardRedirect.as_view()),
    path("leaderboard/", LeaderboardRedirect.as_view()),
]
