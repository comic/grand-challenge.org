from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import re_path, path
from django.views.generic import TemplateView, RedirectView

from grandchallenge.pages.views import FaviconView
from grandchallenge.core.views import comicmain
from grandchallenge.uploads.views import serve

admin.autodiscover()


def handler500(request):
    context = {"request": request}
    template_name = "500.html"
    return TemplateResponse(request, template_name, context, status=500)


urlpatterns = [
    # main page
    url(r"^$", comicmain, name="home"),
    url(
        r"^robots\.txt/$",
        TemplateView.as_view(
            template_name="robots.txt", content_type="text/plain"
        ),
    ),
    # Favicons
    path(
        "favicon.ico/", FaviconView.as_view(rel="shortcut icon"), name="favicon"
    ),
    path(
        "apple-touch-icon.png/",
        FaviconView.as_view(rel="apple-touch-icon"),
        name="apple-touch-icon",
    ),
    path(
        "apple-touch-icon-precomposed.png/",
        FaviconView.as_view(rel="apple-touch-icon-precomposed"),
        name="apple-touch-icon-precomposed",
    ),
    path(
        "apple-touch-icon-<int:size>x<int>.png/",
        FaviconView.as_view(rel="apple-touch-icon"),
        name="apple-touch-icon-sized",
    ),
    path(
        "apple-touch-icon-<int:size>x<int>-precomposed.png/",
        FaviconView.as_view(rel="apple-touch-icon-precomposed"),
        name="apple-touch-icon-precomposed-sized",
    ),
    url(settings.ADMIN_URL, admin.site.urls),
    url(r"^site/", include("grandchallenge.core.urls"), name="site"),
    # Do not change the namespace without updating the view names in
    # evaluation.serializers
    url(r"^api/", include("grandchallenge.api.urls", namespace="api")),
    # Used for logging in and managing grandchallenge.profiles. This is done on
    # the framework level because it is too hard to get this all under each
    # project
    url(r"^accounts/", include("grandchallenge.profiles.urls")),
    url(r"^socialauth/", include("social_django.urls", namespace="social")),
    url(
        r"^challenges/",
        include("grandchallenge.challenges.urls", namespace="challenges"),
    ),
    re_path(
        r"^(?i)all_challenges/$",
        RedirectView.as_view(pattern_name="challenges:list", permanent=False),
    ),
    path("cases/", include("grandchallenge.cases.urls", namespace="cases")),
    path(
        "algorithms/",
        include("grandchallenge.algorithms.urls", namespace="algorithms"),
    ),
    # ========== catch all ====================
    # when all other urls have been checked, try to load page from main project
    # keep this url at the bottom of this list, because urls are checked in
    # order
    url(r"^(?P<page_title>[\w-]+)/$", comicmain, name="mainproject-home"),
    url(r"^media/(?P<challenge_short_name>[\w-]+)/(?P<path>.*)$", serve),
]
if settings.DEBUG and settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns = [
        url(r"^__debug__/", include(debug_toolbar.urls))
    ] + urlpatterns
