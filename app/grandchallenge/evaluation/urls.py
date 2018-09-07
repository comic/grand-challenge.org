from django.urls import path

from grandchallenge.evaluation.forms import (
    method_upload_widget,
    submission_upload_widget,
)
from grandchallenge.evaluation.views import (
    MethodCreate,
    SubmissionCreate,
    JobCreate,
    MethodList,
    SubmissionList,
    JobList,
    ResultList,
    MethodDetail,
    SubmissionDetail,
    JobDetail,
    ResultDetail,
    ConfigUpdate,
    ResultUpdate,
    LegacySubmissionCreate,
)

app_name = "evaluation"

urlpatterns = [
    path("config/", ConfigUpdate.as_view(), name="config-update"),
    path("methods/", MethodList.as_view(), name="method-list"),
    path("methods/create/", MethodCreate.as_view(), name="method-create"),
    path(
        f"methods/create/{method_upload_widget.ajax_target_path}",
        method_upload_widget.handle_ajax,
        name="method-upload-ajax",
    ),
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
        f"submissions/create-legacy/{submission_upload_widget.ajax_target_path}",
        submission_upload_widget.handle_ajax,
        name="submission-upload-legacy-ajax",
    ),
    path(
        f"submissions/create/{submission_upload_widget.ajax_target_path}",
        submission_upload_widget.handle_ajax,
        name="submission-upload-ajax",
    ),
    path(
        "submissions/<uuid:pk>/",
        SubmissionDetail.as_view(),
        name="submission-detail",
    ),
    path("jobs/", JobList.as_view(), name="job-list"),
    path("jobs/create/", JobCreate.as_view(), name="job-create"),
    path("jobs/<uuid:pk>/", JobDetail.as_view(), name="job-detail"),
    path("results/", ResultList.as_view(), name="result-list"),
    path("results/<uuid:pk>/", ResultDetail.as_view(), name="result-detail"),
    path(
        "results/<uuid:pk>/update/",
        ResultUpdate.as_view(),
        name="result-update",
    ),
]
