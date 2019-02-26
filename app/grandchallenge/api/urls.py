from django.conf.urls import include
from django.urls import path
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework_swagger.views import get_swagger_view

from grandchallenge.api.views import (
    UserViewSet,
    GroupViewSet,
    rest_api_complete,
    rest_api_auth,
    CurrentUserView,
)
from grandchallenge.eyra_algorithms.viewsets import AlgorithmViewSet, JobViewSet, InterfaceViewSet
from grandchallenge.eyra_benchmarks.viewsets import BenchmarkViewSet, SubmissionViewSet
from grandchallenge.eyra_data.viewsets import DataFileViewSet, DataTypeViewSet

app_name = "api"

router = routers.DefaultRouter()
# router.register(r"submissions", SubmissionViewSet)
# router.register(r"cases/images", ImageViewSet)

router.register(r"benchmarks", BenchmarkViewSet)
router.register(r"submissions", SubmissionViewSet)
router.register(r"algorithms", AlgorithmViewSet)
router.register(r"interfaces", InterfaceViewSet)
router.register(r"jobs", JobViewSet)
# router.register(r"challenges", ChallengeViewSet)


router.register(r"data_files", DataFileViewSet)
router.register(r"data_types", DataTypeViewSet)
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
