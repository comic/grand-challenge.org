from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import re_path, path
from django.views.generic import TemplateView, RedirectView

from grandchallenge.core.views import comicmain
from grandchallenge.pages.views import FaviconView

admin.autodiscover()


def handler500(request):
    context = {"request": request}
    template_name = "500.html"
    return TemplateResponse(request, template_name, context, status=500)


urlpatterns = [
    path("", comicmain, name="home"),
    path(
        "robots.txt/",
        TemplateView.as_view(
            template_name="robots.txt", content_type="text/plain"
        ),
    ),
    # Favicons
    path(
        "favicon.ico/",
        FaviconView.as_view(rel="shortcut icon"),
        name="favicon",
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
    path(settings.ADMIN_URL, admin.site.urls),
    path("summernote/", include("django_summernote.urls")),
    path(
        "site/<slug:challenge_short_name>/",
        include("grandchallenge.core.urls"),
        name="site",
    ),
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
    path(
        "all_challenges/",
        RedirectView.as_view(pattern_name="challenges:list", permanent=False),
    ),
    path(
        "All_Challenges/",
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
    path("<slug:page_title>/", comicmain, name="mainproject-home"),
    path(
        "media/", include("grandchallenge.serving.urls", namespace="serving")
    ),
]
if settings.DEBUG and settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls))
    ] + urlpatterns
