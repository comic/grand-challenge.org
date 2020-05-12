from django.conf import settings
from django.urls import include, path
from django.views.generic import TemplateView

from grandchallenge.challenges.views import ChallengeUpdate

urlpatterns = [
    path(
        "robots.txt/",
        TemplateView.as_view(
            template_name="robots.txt", content_type="text/plain"
        ),
        name="subdomain_robots_txt",
    ),
    path(
        "",
        include(
            "grandchallenge.favicons.urls", namespace="subdomain-favicons"
        ),
    ),
    path(
        "evaluation/",
        include("grandchallenge.evaluation.urls", namespace="evaluation"),
    ),
    path("teams/", include("grandchallenge.teams.urls", namespace="teams")),
    path(
        "participants/",
        include("grandchallenge.participants.urls", namespace="participants"),
    ),
    path("admins/", include("grandchallenge.admins.urls", namespace="admins")),
    path(
        "datasets/",
        include("grandchallenge.datasets.urls", namespace="datasets"),
    ),
    path("update/", ChallengeUpdate.as_view(), name="update"),
    path("summernote/", include("django_summernote.urls")),
    path("", include("grandchallenge.pages.urls", namespace="pages")),
]

if settings.DEBUG and settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls))
    ] + urlpatterns
