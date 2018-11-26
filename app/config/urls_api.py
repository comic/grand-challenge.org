from django.conf import settings
from django.conf.urls import include
from django.template.response import TemplateResponse
from django.urls import re_path, path

def handler500(request):
    context = {"request": request}
    template_name = "500.html"
    return TemplateResponse(request, template_name, context, status=500)


urlpatterns = [
    # Do not change the api namespace without updating the view names in
    # all of the serializers
    # path("api/v2/socialauth/", include("social_django.urls", namespace="social")),
    path("api/v2/", include("grandchallenge.api2.urls", namespace="api2")),
    path("api/v2/auth/", include('rest_framework_social_oauth2.urls')),

]
if settings.DEBUG and settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls))
    ] + urlpatterns
