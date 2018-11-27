from django.conf.urls import include
from django.urls import path
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework_swagger.views import get_swagger_view
from social_django.views import auth

from grandchallenge.api.views import SubmissionViewSet, complete
from grandchallenge.cases.views import ImageViewSet
from grandchallenge.challenges.viewsets import ChallengeViewSet

app_name = "api"

router = routers.DefaultRouter()
router.register(r"submissions", SubmissionViewSet)
router.register(r"cases/images", ImageViewSet)
router.register(r"challenges", ChallengeViewSet)

urlpatterns_social = [
    path("login/<backend>/", auth, name='begin'),
    path("complete/<backend>/", complete, name='complete'),
]

urlpatterns = [
    # Do not namespace the router.urls without updating the view names in
    # evaluation.serializers
    path("v1/", include(router.urls)),
    path("auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("spec/", get_swagger_view(title='Comic API')),
    path("social/", include((urlpatterns_social, 'social'))),
    path("obtain_token/", obtain_auth_token),
]
