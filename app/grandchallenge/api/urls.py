from django.conf.urls import include
from django.urls import path
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework_swagger.views import get_swagger_view

from grandchallenge.api.views import (
    SubmissionViewSet,
    UserViewSet,
    GroupViewSet,
    rest_api_complete,
    rest_api_auth,
    CurrentUserView,
)
from grandchallenge.cases.views import ImageViewSet
from grandchallenge.challenges.viewsets import ChallengeViewSet
from grandchallenge.eyra_benchmarks.viewsets import EyraBenchmarkViewSet
from grandchallenge.eyra_data.viewsets import DataFileViewSet, DataTypeViewSet

app_name = "api"

router = routers.DefaultRouter()
router.register(r"submissions", SubmissionViewSet)
router.register(r"cases/images", ImageViewSet)

router.register(r"benchmarks", EyraBenchmarkViewSet)
# router.register(r"challenges", ChallengeViewSet)


router.register(r"datasets", DataFileViewSet)
router.register(r"datasettypes", DataTypeViewSet)
# router.register(r"datasetfiles", DataSetFileViewSet)

router.register(r"users", UserViewSet)
router.register(r"groups", GroupViewSet)

urlpatterns_social = [
    path("login/<backend>/", rest_api_auth, name="begin"),
    path("complete/<backend>/", rest_api_complete, name="complete"),
]

urlpatterns = [
    path(
        "v1/auth/", include("rest_framework.urls", namespace="rest_framework")
    ),
    # path('v1/datasetfiles/<str:uuid>/', upload_file),
    path("v1/me/", CurrentUserView.as_view()),
    path("v1/spec/", get_swagger_view(title="Comic API")),
    path("v1/social/", include((urlpatterns_social, "social"))),
    path("v1/login/", obtain_auth_token),
    # Do not namespace the router.urls without updating the view names in
    # evaluation.serializers
    path("v1/", include(router.urls)),
]
