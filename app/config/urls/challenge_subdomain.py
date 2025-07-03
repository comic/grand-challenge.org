from django.conf import settings
from django.urls import include, path

from grandchallenge.challenges.views import (
    ChallengeUpdate,
    OnboardingTaskComplete,
    OnboardingTaskList,
)

handler403 = "grandchallenge.core.views.handler403"
handler404 = "grandchallenge.core.views.handler404"
handler500 = "grandchallenge.core.views.handler500"


urlpatterns = [
    path(
        "", include("grandchallenge.well_known.urls", namespace="well-known")
    ),
    path(
        "evaluation/",
        include("grandchallenge.evaluation.urls", namespace="evaluation"),
    ),
    path(
        "invoices/",
        include("grandchallenge.invoices.urls", namespace="invoices"),
    ),
    path("teams/", include("grandchallenge.teams.urls", namespace="teams")),
    path(
        "participants/",
        include("grandchallenge.participants.urls", namespace="participants"),
    ),
    path("admins/", include("grandchallenge.admins.urls", namespace="admins")),
    path(
        "challenge/update/", ChallengeUpdate.as_view(), name="challenge-update"
    ),
    path(
        "onboarding-tasks/all/",
        OnboardingTaskList.as_view(),
        name="challenge-onboarding-task-list",
    ),
    path(
        "onboarding-tasks/<uuid:pk>/complete/",
        OnboardingTaskComplete.as_view(),
        name="challenge-onboarding-task-complete",
    ),
    path("markdownx/", include("markdownx.urls")),
    path("", include("grandchallenge.pages.urls", namespace="pages")),
]

if settings.DEBUG and settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls))
    ] + urlpatterns
