from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path
from django.views.generic import TemplateView

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
        "workstations/<slug>/sessions/<uuid:pk>/",
        SessionDetail.as_view(),
        name="session-detail",
    ),
    path(
        "workstations/<slug>/sessions/<uuid:pk>/<path:path>",
        session_proxy,
        name="session-proxy",
    ),
]
