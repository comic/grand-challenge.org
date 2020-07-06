from django.urls import path

from grandchallenge.evaluation.views import (
    ConfigUpdate,
    JobDetail,
    JobList,
    JobUpdate,
    Leaderboard,
    LegacySubmissionCreate,
    MethodCreate,
    MethodDetail,
    MethodList,
    SubmissionCreate,
    SubmissionDetail,
    SubmissionList,
)

app_name = "evaluation"

urlpatterns = [
    path("config/", ConfigUpdate.as_view(), name="config-update"),
    path("methods/", MethodList.as_view(), name="method-list"),
    path("methods/create/", MethodCreate.as_view(), name="method-create"),
    path("methods/<uuid:pk>/", MethodDetail.as_view(), name="method-detail"),
    path("submissions/", SubmissionList.as_view(), name="submission-list"),
    path(
        "submissions/create/",
        SubmissionCreate.as_view(),
        name="submission-create",
    ),
    path(
        "submissions/create-legacy/",
        LegacySubmissionCreate.as_view(),
        name="submission-create-legacy",
    ),
    path(
        "submissions/<uuid:pk>/",
        SubmissionDetail.as_view(),
        name="submission-detail",
    ),
    path("jobs/", JobList.as_view(), name="job-list"),
    path("jobs/<uuid:pk>/", JobDetail.as_view(), name="job-detail"),
    path("jobs/<uuid:pk>/update/", JobUpdate.as_view(), name="job-update",),
    path("results/", Leaderboard.as_view(), name="leaderboard"),
]
