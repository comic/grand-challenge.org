from django.conf.urls import include
from django.urls import path
# from drf_yasg import openapi
# from drf_yasg.views import get_schema_view
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token

from comic.eyra.views import (
    rest_api_complete,
    rest_api_auth,
    CurrentUserView,
)
from comic.eyra.viewsets import BenchmarkViewSet, SubmissionViewSet, AlgorithmViewSet, JobViewSet, DataFileViewSet, \
    DataSetViewSet, UserViewSet, GroupViewSet, RegisterViewSet, LoginView

app_name = "api"

router = routers.DefaultRouter()

router.register(r"benchmarks", BenchmarkViewSet)
router.register(r"submissions", SubmissionViewSet)
router.register(r"algorithms", AlgorithmViewSet)
router.register(r"jobs", JobViewSet)
router.register(r"data_files", DataFileViewSet, base_name='data_files')
router.register(r"data_sets", DataSetViewSet)
router.register(r"users", UserViewSet)
router.register(r"groups", GroupViewSet)

urlpatterns_social = [
    path("login/<backend>/", rest_api_auth, name="begin"),
    path("complete/<backend>/", rest_api_complete, name="complete"),
]

urlpatterns = [
    path("v1/auth/register/", RegisterViewSet.as_view({'post': 'create'})),
    path("v1/auth/login/", LoginView.as_view()),
    # path("v1/algorithmSubmission/", algorithm_submission),
    path("v1/social/", include((urlpatterns_social, "social"))),
    path("v1/me/", CurrentUserView.as_view()),
    path("v1/login/", obtain_auth_token),
    path("v1/", include(router.urls), name='drf'),
]
#
# schema_view = get_schema_view(
#    openapi.Info(
#       title="Eyra Benchmark REST API",
#       default_version='v1',
#       description="Eyra Benchmark REST API v1.",
#       terms_of_service="https://www.eyrabenchmark.net/",
#       contact=openapi.Contact(email="info@eyrabenchmark.net"),
#       license=openapi.License(name="Apache 2.0"),
#    ),
#    validators=['flex', 'ssv'],
#    public=True,
#    permission_classes=(permissions.AllowAny,),
#    patterns=urlpatterns[-3:],
# )

urlpatterns = [
    *urlpatterns[:-1],
    # url(r'^v1/$', schema_view.with_ui('redoc', cache_timeout=None), name='schema-redoc'),
    urlpatterns[-1]
]


