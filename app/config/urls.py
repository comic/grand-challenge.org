from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from django.views.generic import TemplateView

# from grandchallenge.core.views import comicmain
# from grandchallenge.pages.views import FaviconView

admin.autodiscover()


def handler500(request):
    context = {"request": request}
    template_name = "500.html"
    return TemplateResponse(request, template_name, context, status=500)


urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    # Do not change the api namespace without updating the view names in
    # all of the serializers
    path("api/", include("grandchallenge.api.urls", namespace="api")),
    # Used for logging in and managing grandchallenge.profiles. This is done on
    # the framework level because it is too hard to get this all under each
    # project
    # path("socialauth/", include("social_django.urls", namespace="social")),
    # path(
    #     "media/",
    #     include("grandchallenge.serving.urls", namespace="root-serving"),
    # ),
]
if settings.DEBUG and settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls))
    ] + urlpatterns
