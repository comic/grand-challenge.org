from django.conf.urls import include
from django.urls import path
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token

from grandchallenge.api.views import SubmissionViewSet
from grandchallenge.cases.views import ImageViewSet
from grandchallenge.challenges.viewsets import ChallengeViewSet

app_name = "api2"

router = routers.DefaultRouter()
router.register(r"challenges", ChallengeViewSet)
# router.register(r"submissions", SubmissionViewSet)
# router.register(r"cases/images", ImageViewSet)
urlpatterns = [
    # Do not namespace the router.urls without updating the view names in
    # evaluation.serializers
    path("", include(router.urls)),
    path("obtain_token/", obtain_auth_token),
]
