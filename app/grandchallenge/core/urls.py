from django.conf.urls import include
from django.urls import path
from django.views.generic import TemplateView, RedirectView

from grandchallenge.core.api import get_public_results
from grandchallenge.core.views import site
from grandchallenge.serving.views import ChallengeServeRedirect

urlpatterns = [
    path("<slug:challenge_short_name>/", site, name="challenge-homepage"),
    path(
        "<slug:challenge_short_name>/robots.txt/",
        TemplateView.as_view(
            template_name="robots.txt", content_type="text/plain"
        ),
        name="comicsite_robots_txt",
    ),
    # Note: add new namespaces to comic_URLNode(defaulttags.URLNode)
    path(
        "<slug:challenge_short_name>/evaluation/",
        include("grandchallenge.evaluation.urls", namespace="evaluation"),
    ),
    path(
        "<slug:challenge_short_name>/teams/",
        include("grandchallenge.teams.urls", namespace="teams"),
    ),
    path(
        "<slug:challenge_short_name>/participants/",
        include("grandchallenge.participants.urls", namespace="participants"),
    ),
    path(
        "<slug:challenge_short_name>/admins/",
        include("grandchallenge.admins.urls", namespace="admins"),
    ),
    path(
        "<slug:challenge_short_name>/uploads/",
        include("grandchallenge.uploads.urls", namespace="uploads"),
    ),
    path(
        "<slug:challenge_short_name>/datasets/",
        include("grandchallenge.datasets.urls", namespace="datasets"),
    ),
    #################
    #
    # Legacy apps
    #
    path(
        "<slug:challenge_short_name>/files/$",
        RedirectView.as_view(pattern_name="uploads:create", permanent=False),
    ),
    path(
        "<slug:challenge_short_name>/serve/<path:path>/",
        ChallengeServeRedirect.as_view(),
        name="project_serve_file",
    ),
    path(
        "<slug:challenge_short_name>/api/get_public_results/",
        get_public_results,
    ),
    #
    # End Legacy
    #
    #################
    # If nothing specific matches, try to resolve the url as project/pagename
    path(
        "<slug:challenge_short_name>/",
        include("grandchallenge.pages.urls", namespace="pages"),
    ),
]
