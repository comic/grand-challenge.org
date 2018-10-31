from django.conf.urls import include, url
from django.urls import path
from rest_framework import routers
from rest_framework.authtoken import views as drf_auth_views

from grandchallenge.api.views import SubmissionViewSet
from grandchallenge.cases.views import ImageViewSet

app_name = "api"

router = routers.DefaultRouter()
router.register(r"submissions", SubmissionViewSet)
router.register(r"cases/images", ImageViewSet)
urlpatterns = [
    # Do not namespace the router.urls without updating the view names in
    # evaluation.serializers
    path("v1/", include(router.urls)),
    path("auth/", include("rest_framework.urls", namespace="rest_framework")),
    url("auth/token/", drf_auth_views.obtain_auth_token),
]
