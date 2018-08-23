from django.conf.urls import url, include
from rest_framework import routers

from grandchallenge.api.views import SubmissionViewSet
from grandchallenge.cases.views import AnnotationViewSet, ImageViewSet

app_name = "api"

router = routers.DefaultRouter()
router.register(r"submissions", SubmissionViewSet)
router.register(r"cases/annotations", AnnotationViewSet)
router.register(r"cases/images", ImageViewSet)
urlpatterns = [
    # Do not namespace the router.urls without updating the view names in
    # evaluation.serializers
    url(r"^v1/", include(router.urls)),
    url(r"^auth/", include("rest_framework.urls", namespace="rest_framework")),
]
