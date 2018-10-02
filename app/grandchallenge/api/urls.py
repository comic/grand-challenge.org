from django.conf.urls import include
from django.urls import path
from rest_framework import routers

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
]
