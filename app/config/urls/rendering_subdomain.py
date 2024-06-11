from django.conf import settings
from django.urls import path
from django.views.generic import TemplateView

from grandchallenge.core.views import healthcheck
from grandchallenge.serving.views import serve_images
from grandchallenge.workstations.views import SessionDetail, session_proxy

handler500 = "grandchallenge.core.views.handler500"


urlpatterns = [
    path(
        "robots.txt",
        TemplateView.as_view(
            template_name="robots.txt", content_type="text/plain"
        ),
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
