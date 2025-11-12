from django.conf import settings
from django.urls import include, path, register_converter

from grandchallenge.core.views import healthcheck
from grandchallenge.serving.urls import HexByteConverter
from grandchallenge.serving.views import serve_images
from grandchallenge.workstations.views import SessionDetail, session_proxy

handler403 = "grandchallenge.core.views.handler403"
handler404 = "grandchallenge.core.views.handler404"
handler500 = "grandchallenge.core.views.handler500"

register_converter(HexByteConverter, "hexbyte")

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
        f"media/{settings.IMAGE_FILES_SUBDIRECTORY}/<hexbyte:pa>/<hexbyte:pb>/<uuid:pk>/<path:path>",
        serve_images,
    ),
]
