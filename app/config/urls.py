from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from django.views.generic import TemplateView

from grandchallenge.core.views import HomeTemplate

admin.autodiscover()


def handler500(request):
    context = {"request": request}
    template_name = "500.html"
    return TemplateResponse(request, template_name, context, status=500)


urlpatterns = [
    path("", HomeTemplate.as_view(), name="home"),
    path(
        "robots.txt/",
        TemplateView.as_view(
            template_name="robots.txt", content_type="text/plain"
        ),
    ),
    path("", include("grandchallenge.favicons.urls", namespace="favicons")),
    path(settings.ADMIN_URL, admin.site.urls),
    path(
        "stats/",
        include("grandchallenge.statistics.urls", namespace="statistics"),
    ),
    # Do not change the api namespace without updating the view names in
    # all of the serializers
    path("api/", include("grandchallenge.api.urls", namespace="api")),
    # Used for logging in and managing grandchallenge.profiles. This is done on
    # the framework level because it is too hard to get this all under each
    # project
    path("accounts/", include("grandchallenge.profiles.urls")),
    path("socialauth/", include("social_django.urls", namespace="social")),
    path(
        "challenges/",
        include("grandchallenge.challenges.urls", namespace="challenges"),
    ),
    path("cases/", include("grandchallenge.cases.urls", namespace="cases")),
    path(
        "algorithms/",
        include("grandchallenge.algorithms.urls", namespace="algorithms"),
    ),
    path(
        "workstations/",
        include("grandchallenge.workstations.urls", namespace="workstations"),
    ),
    path(
        "reader-studies/",
        include(
            "grandchallenge.reader_studies.urls", namespace="reader-studies"
        ),
    ),
    path(
        "workstation-configs/",
        include(
            "grandchallenge.workstation_configs.urls",
            namespace="workstation-configs",
        ),
    ),
    path("summernote/", include("django_summernote.urls")),
    path(
        "retina/",
        include("grandchallenge.retina_core.urls", namespace="retina"),
    ),
    path(
        "registrations/",
        include(
            "grandchallenge.registrations.urls", namespace="registrations"
        ),
    ),
    path(
        "policies/",
        include("grandchallenge.policies.urls", namespace="policies"),
    ),
    path(
        "media/", include("grandchallenge.serving.urls", namespace="serving"),
    ),
]

if settings.DEBUG and settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls))
    ] + urlpatterns
