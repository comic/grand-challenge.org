from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import RedirectView

from grandchallenge.algorithms.sitemaps import AlgorithmsSitemap
from grandchallenge.archives.sitemaps import ArchivesSitemap
from grandchallenge.blogs.sitemaps import PostsSitemap
from grandchallenge.challenges.sitemaps import ChallengesSitemap
from grandchallenge.core.sitemaps import CoreSitemap, FlatPagesSitemap
from grandchallenge.core.views import (
    ChallengeSuspendedView,
    HomeTemplate,
    RedirectPath,
    healthcheck,
)
from grandchallenge.pages.sitemaps import PagesSitemap
from grandchallenge.policies.sitemaps import PoliciesSitemap
from grandchallenge.reader_studies.sitemaps import ReaderStudiesSiteMap

admin.autodiscover()
admin.site.login = login_required(admin.site.login)

handler403 = "grandchallenge.core.views.handler403"
handler404 = "grandchallenge.core.views.handler404"
handler500 = "grandchallenge.core.views.handler500"


sitemaps = {
    "algorithms": AlgorithmsSitemap,
    "archives": ArchivesSitemap,
    "blogs": PostsSitemap,
    "challenges": ChallengesSitemap,
    "core": CoreSitemap,
    "flatpages": FlatPagesSitemap,
    "pages": PagesSitemap,
    "policies": PoliciesSitemap,
    "reader-studies": ReaderStudiesSiteMap,
}

urlpatterns = [
    path(
        "", include("grandchallenge.well_known.urls", namespace="well-known")
    ),
    path("", HomeTemplate.as_view(), name="home"),
    path(
        "challenge-suspended/",
        ChallengeSuspendedView.as_view(),
        name="challenge-suspended",
    ),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path(
        "healthcheck/",
        healthcheck,
    ),
    path(
        f"{settings.ADMIN_URL}/login/",
        RedirectView.as_view(url=settings.LOGIN_URL),
    ),
    path(
        f"{settings.ADMIN_URL}/logout/",
        RedirectView.as_view(url=settings.LOGOUT_URL),
    ),
    path(f"{settings.ADMIN_URL}/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path(
        "stats/",
        include("grandchallenge.statistics.urls", namespace="statistics"),
    ),
    # Do not change the api namespace without updating the view names in
    # all of the serializers
    path("api/", include("grandchallenge.api.urls", namespace="api")),
    path("github/", include("grandchallenge.github.urls", namespace="github")),
    path("users/", include("grandchallenge.profiles.urls")),
    path(
        "notifications/",
        include(
            "grandchallenge.notifications.urls", namespace="notifications"
        ),
    ),
    path(
        "settings/api-tokens/",
        include("grandchallenge.api_tokens.urls", namespace="api-tokens"),
    ),
    path(
        "verifications/",
        include(
            "grandchallenge.verifications.urls", namespace="verifications"
        ),
    ),
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
        "archives/",
        include("grandchallenge.archives.urls", namespace="archives"),
    ),
    path(
        "viewers/",
        include("grandchallenge.workstations.urls", namespace="workstations"),
    ),
    path(
        "reader-studies/",
        include(
            "grandchallenge.reader_studies.urls", namespace="reader-studies"
        ),
    ),
    path(
        "viewer-configurations/",
        include(
            "grandchallenge.workstation_configs.urls",
            namespace="workstation-configs",
        ),
    ),
    path(
        "aiforradiology/",
        RedirectPath.as_view(
            netloc="radiology.healthairegister.com", permanent=True
        ),
    ),
    path(
        "aiforradiology/<path:path>",
        RedirectPath.as_view(
            netloc="radiology.healthairegister.com", permanent=True
        ),
    ),
    path(
        "policies/",
        include("grandchallenge.policies.urls", namespace="policies"),
    ),
    path("markdownx/", include("markdownx.urls")),
    path(
        "media/", include("grandchallenge.serving.urls", namespace="serving")
    ),
    path("blogs/", include("grandchallenge.blogs.urls", namespace="blogs")),
    path(
        "organizations/",
        include(
            "grandchallenge.organizations.urls", namespace="organizations"
        ),
    ),
    path(
        "publications/",
        include("grandchallenge.publications.urls", namespace="publications"),
    ),
    path(
        "documentation/",
        include(
            "grandchallenge.documentation.urls", namespace="documentation"
        ),
    ),
    path(
        "flatpages/",
        include("grandchallenge.flatpages.urls", namespace="flatpages"),
    ),
    path(
        "hanging-protocols/",
        include(
            "grandchallenge.hanging_protocols.urls",
            namespace="hanging-protocols",
        ),
    ),
    path("emails/", include("grandchallenge.emails.urls", namespace="emails")),
    path(
        "components/",
        include("grandchallenge.components.urls", namespace="components"),
    ),
    path(
        "messages/",
        include(
            "grandchallenge.direct_messages.urls", namespace="direct-messages"
        ),
    ),
]

if settings.DEBUG and settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls))
    ] + urlpatterns
