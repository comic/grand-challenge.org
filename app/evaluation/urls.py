from django.conf.urls import url, include
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token

from evaluation.views import ResultViewSet, SubmissionViewSet, JobViewSet, \
    MethodViewSet

router = routers.DefaultRouter()
router.register(r'results', ResultViewSet, base_name='results')
router.register(r'submissions', SubmissionViewSet, base_name='submissions')
router.register(r'jobs', JobViewSet, base_name='jobs')
router.register(r'methods', MethodViewSet, base_name='methods')

urlpatterns = [
    url(r'^api/v1/', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
    url(r'^api-token-auth/', obtain_auth_token)
]
