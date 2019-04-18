from django.conf.urls import include, url
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers, permissions
from rest_framework.authtoken.views import obtain_auth_token
# from rest_framework_swagger.views import get_swagger_view

from grandchallenge.api.views import (
    UserViewSet,
    GroupViewSet,
    rest_api_complete,
    rest_api_auth,
    CurrentUserView,
)
from grandchallenge.eyra_algorithms.viewsets import ImplementationViewSet, JobViewSet, InterfaceViewSet, \
    AlgorithmViewSet
from grandchallenge.eyra_benchmarks.viewsets import BenchmarkViewSet, SubmissionViewSet, algorithm_submission
from grandchallenge.eyra_data.viewsets import DataFileViewSet, DataTypeViewSet, DataSetViewSet
from grandchallenge.eyra_users.viewsets import RegisterViewSet, LoginView

app_name = "api"

router = routers.DefaultRouter()
# router.register(r"submissions", SubmissionViewSet)
# router.register(r"cases/images", ImageViewSet)

# router.register(r"benchmarks", BenchmarkViewSet)
router.register(r"submissions", SubmissionViewSet)
router.register(r"implementations", ImplementationViewSet)
router.register(r"algorithms", AlgorithmViewSet)
router.register(r"interfaces", InterfaceViewSet)
router.register(r"jobs", JobViewSet)
# router.register(r"challenges", ChallengeViewSet)


router.register(r"data_files", DataFileViewSet)
router.register(r"data_types", DataTypeViewSet)
router.register(r"data_sets", DataSetViewSet)
# router.register(r"datasetfiles", DataSetFileViewSet)

router.register(r"users", UserViewSet)
router.register(r"groups", GroupViewSet)

urlpatterns_social = [
    path("login/<backend>/", rest_api_auth, name="begin"),
    path("complete/<backend>/", rest_api_complete, name="complete"),
]

schema_view = get_schema_view(
   openapi.Info(
      title="Snippets API",
      default_version='v1',
      description="Test description",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),
   ),
   validators=['flex', 'ssv'],
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("v1/auth/register/", RegisterViewSet.as_view({'post': 'create'})),
    path("v1/auth/login/", LoginView.as_view()),
    path("v1/algorithmSubmission/", algorithm_submission),

    # path('v1/datasetfiles/<str:uuid>/', upload_file),
    path("v1/me/", CurrentUserView.as_view()),
    # path("v1/spec/", get_swagger_view(title="Comic API")),
    path("v1/social/", include((urlpatterns_social, "social"))),
    path("v1/login/", obtain_auth_token),
    # Do not namespace the router.urls without updating the view names in
    # evaluation.serializers
    url(r'^v1/$', schema_view.with_ui('redoc', cache_timeout=None), name='schema-redoc'),

    path("v1/", include(router.urls)),
]

