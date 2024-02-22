from django.conf import settings
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path
from django.views.generic import TemplateView

from grandchallenge.core.views import healthcheck
from grandchallenge.serving.views import (
    serve_component_interface_value,
    serve_images,
)
from grandchallenge.workstations.views import SessionDetail, session_proxy


def handler404(request, exception):
    domain = request.site.domain.lower()
    return HttpResponseRedirect(
        f"{request.scheme}://{domain}{request.get_full_path()}"
    )


def handler500(request):
    context = {"request": request}
    template_name = "500.html"
    return TemplateResponse(request, template_name, context, status=500)


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
    path(
        (
            f"media/"
            f"{settings.COMPONENTS_FILES_SUBDIRECTORY}/"
            f"componentinterfacevalue/"
            f"<prefix:pa>/"
            f"<prefix:pb>/"
            f"<int:component_interface_value_pk>/"
            f"<path:path>"
        ),
        serve_component_interface_value,
    ),
]
