from django.conf import settings
from django.urls import include, path
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic import TemplateView
from django.views import defaults as default_views
from .views import IndexView


app_name = 'retina'
urlpatterns = [
    # path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path("", IndexView.as_view(), name="home"),
    path("api/", include("grandchallenge.retina_api.urls")),
    path("archives/", include("grandchallenge.archives.urls")),
    path("patients/", include("grandchallenge.patients.urls")),
    path("studies/", include("grandchallenge.studies.urls")),
    path("retina_images/", include("grandchallenge.retina_images.urls")),
    path("annotations/", include("grandchallenge.annotations.urls")),
    path("retina_importers/", include("grandchallenge.retina_importers.urls")),
    path("registrations/", include("grandchallenge.registrations.urls")),
]

# if settings.DEBUG:
#     # This allows the error pages to be debugged during development, just visit
#     # these url in browser to see how these error pages look like.
#     urlpatterns += [
#         path(
#             "400/",
#             default_views.bad_request,
#             kwargs={"exception": Exception("Bad Request!")},
#         ),
#         path(
#             "403/",
#             default_views.permission_denied,
#             kwargs={"exception": Exception("Permission Denied")},
#         ),
#         path(
#             "404/",
#             default_views.page_not_found,
#             kwargs={"exception": Exception("Page not Found")},
#         ),
#         path("500/", default_views.server_error),
#     ]
#     if "debug_toolbar" in settings.INSTALLED_APPS:
#         import debug_toolbar
#
#         urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
