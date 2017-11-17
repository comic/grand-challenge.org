from django.conf.urls import url, include
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token

from evaluation.forms import test_upload_widget, test_upload_widget2
from evaluation.views import ResultViewSet, SubmissionViewSet, JobViewSet, \
    MethodViewSet, uploader_widget_test, MethodCreate, SubmissionCreate, \
    JobCreate, MethodList, SubmissionList, JobList, ResultList, MethodDetail, \
    SubmissionDetail, JobDetail, ResultDetail

router = routers.DefaultRouter()
router.register(r'results', ResultViewSet)
router.register(r'submissions', SubmissionViewSet)
router.register(r'jobs', JobViewSet)
router.register(r'methods', MethodViewSet)

urlpatterns = [
    url(r'^methods/$', MethodList.as_view()),
    url(r'^methods/add/$', MethodCreate.as_view()),
    url(r'^methods/(?P<pk>[0-9a-fA-F-]+)/$', MethodDetail.as_view()),
    url(r'^submissions/$', SubmissionList.as_view()),
    url(r'^submissions/add/$', SubmissionCreate.as_view()),
    url(r'^submissions/(?P<pk>[0-9a-fA-F-]+)/$', SubmissionDetail.as_view()),
    url(r'^jobs/$', JobList.as_view()),
    url(r'^jobs/add/$', JobCreate.as_view()),
    url(r'^jobs/(?P<pk>[0-9a-fA-F-]+)/$', JobDetail.as_view()),
    url(r'^results/$', ResultList.as_view()),
    url(r'^results/(?P<pk>[0-9a-fA-F-]+)/$', ResultDetail.as_view()),
    url(r'^api/v1/', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
    url(r'^api-token-auth/', obtain_auth_token),
    url(f'^{test_upload_widget.ajax_target_path}',
        test_upload_widget.handle_ajax),
    url(f'^{test_upload_widget2.ajax_target_path}',
        test_upload_widget2.handle_ajax),
    url(r'^testwidget', uploader_widget_test),
]
