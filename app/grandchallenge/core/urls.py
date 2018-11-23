from django.conf.urls import include
from django.urls import path
from django.views.generic import TemplateView, RedirectView

from grandchallenge.core.views import site
from grandchallenge.serving.views import ChallengeServeRedirect

urlpatterns = [
    path("", site, name="challenge-homepage"),
    path(
        "robots.txt/",
        TemplateView.as_view(
            template_name="robots.txt", content_type="text/plain"
        ),
        name="comicsite_robots_txt",
    ),
    # Note: add new namespaces to comic_URLNode(defaulttags.URLNode)
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
        "uploads/", include("grandchallenge.uploads.urls", namespace="uploads")
    ),
    path(
        "datasets/",
        include("grandchallenge.datasets.urls", namespace="datasets"),
    ),
    #################
    #
    # Legacy apps
    #
    path(
        "files/",
        RedirectView.as_view(pattern_name="uploads:create", permanent=False),
    ),
    path(
        "serve/<path:path>/",
        ChallengeServeRedirect.as_view(),
        name="project_serve_file",
    ),
    #
    # End Legacy
    #
    #################
    # If nothing specific matches, try to resolve the url as project/pagename
    path("", include("grandchallenge.pages.urls", namespace="pages")),
]
