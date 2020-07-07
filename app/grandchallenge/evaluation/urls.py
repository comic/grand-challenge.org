from django.urls import path
from django.views.generic import RedirectView

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
    path("leaderboard/", Leaderboard.as_view(), name="leaderboard"),
    path("", JobList.as_view(), name="job-list"),
    path("<uuid:pk>/", JobDetail.as_view(), name="job-detail"),
    path("<uuid:pk>/update/", JobUpdate.as_view(), name="job-update"),
    path(
        "results/", RedirectView.as_view(url="../leaderboard/", permanent=True)
    ),
]
