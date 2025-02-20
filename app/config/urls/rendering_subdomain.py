from django.conf import settings
from django.urls import include, path

from grandchallenge.core.views import healthcheck
from grandchallenge.serving.views import serve_images
from grandchallenge.workstations.views import SessionDetail, session_proxy

handler500 = "grandchallenge.core.views.handler500"


urlpatterns = [
    path(
        "", include("grandchallenge.well_known.urls", namespace="well-known")
    ),
    path(
        "healthcheck/",
        healthcheck,
    ),
    path(
        "workstations/<slug>/sessions/<uuid:pk>/",
        SessionDetail.as_view(),
        name="session-detail",
    ),
    path(
        "workstations/<slug>/sessions/<uuid:pk>/<path:path>",
        session_proxy,
        name="session-proxy",
    ),
    path(
        f"media/{settings.IMAGE_FILES_SUBDIRECTORY}/<prefix:pa>/<prefix:pb>/<uuid:pk>/<path:path>",
        serve_images,
    ),
]
