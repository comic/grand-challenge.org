import prometheus_client
from django.conf import settings

WORKSTATION_SESSIONS_ACTIVE = prometheus_client.Gauge(
    "grandchallenge_workstation_sessions_active_total",
    "The number of active workstation sessions",
)
ALGORITHM_JOBS_PENDING = prometheus_client.Gauge(
    "grandchallenge_algorithm_jobs_pending_total",
    "The number of pending algorithm jobs",
)
ALGORITHM_JOBS_ACTIVE = prometheus_client.Gauge(
    "grandchallenge_algorithm_jobs_active_total",
    "The number of active algorithm jobs",
)
EVALUATION_JOBS_PENDING = prometheus_client.Gauge(
    "grandchallenge_evaluation_jobs_pending_total",
    "The number of pending evaluation jobs",
)
EVALUATION_JOBS_ACTIVE = prometheus_client.Gauge(
    "grandchallenge_evaluation_jobs_active_total",
    "The number of active evaluation jobs",
)
UPLOAD_SESSIONS_PENDING = prometheus_client.Gauge(
    "grandchallenge_upload_sessions_pending_total",
    "The number of pending upload sessions",
)
UPLOAD_SESSIONS_ACTIVE = prometheus_client.Gauge(
    "grandchallenge_upload_sessions_active_total",
    "The number of active upload sessions",
)
BUILD_VERSION = prometheus_client.Info(
    "grandchallenge_build_version", "The build version"
)
BUILD_VERSION.info({"grandchallenge_commit_id": settings.COMMIT_ID})
