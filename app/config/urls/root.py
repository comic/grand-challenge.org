from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.template.response import TemplateResponse
from django.urls import path
from django.views.generic import TemplateView

from grandchallenge.algorithms.sitemaps import AlgorithmsSitemap
from grandchallenge.archives.sitemaps import ArchivesSitemap
from grandchallenge.challenges.sitemaps import ChallengesSitemap
from grandchallenge.core.sitemaps import CoreSitemap, FlatPagesSitemap
from grandchallenge.core.views import HomeTemplate
from grandchallenge.overview_pages.sitemaps import OverviewPagesSitemap
from grandchallenge.pages.sitemaps import PagesSitemap
from grandchallenge.policies.sitemaps import PoliciesSitemap
from grandchallenge.products.sitemaps import CompaniesSitemap, ProductsSitemap
from grandchallenge.reader_studies.sitemaps import ReaderStudiesSiteMap

admin.autodiscover()


def handler500(request):
    context = {"request": request}
    template_name = "500.html"
    return TemplateResponse(request, template_name, context, status=500)


sitemaps = {
    "algorithms": AlgorithmsSitemap,
    "archives": ArchivesSitemap,
    "challenges": ChallengesSitemap,
    "companies": CompaniesSitemap,
    "core": CoreSitemap,
    "flatpages": FlatPagesSitemap,
    "overview-pages": OverviewPagesSitemap,
    "pages": PagesSitemap,
    "policies": PoliciesSitemap,
    "products": ProductsSitemap,
    "reader-studies": ReaderStudiesSiteMap,
}

urlpatterns = [
    path("", HomeTemplate.as_view(), name="home"),
    path(
        "robots.txt",
        TemplateView.as_view(
            template_name="robots.txt", content_type="text/plain"
        ),
    ),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
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
    path("users/", include("grandchallenge.profiles.urls")),
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
        "aiforradiology/",
        include("grandchallenge.products.urls", namespace="products"),
    ),
    path(
        "policies/",
        include("grandchallenge.policies.urls", namespace="policies"),
    ),
    path("markdownx/", include("markdownx.urls")),
    path(
        "media/", include("grandchallenge.serving.urls", namespace="serving"),
    ),
    path(
        "",
        include(
            "grandchallenge.overview_pages.urls", namespace="overview-pages"
        ),
    ),
]

if settings.DEBUG and settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls))
    ] + urlpatterns
