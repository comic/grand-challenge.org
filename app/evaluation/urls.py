from django.conf.urls import url, include, patterns
from rest_framework.authtoken.views import obtain_auth_token

from .views import ResultList, SubmissionList, JobList, MethodList

urlpatterns = patterns('',
                       url(r'^api/v1/results/$', ResultList.as_view()),
                       url(r'^api/v1/submissions/$', SubmissionList.as_view()),
                       url(r'^api/v1/jobs/$', JobList.as_view()),
                       url(r'^api/v1/methods/', MethodList.as_view()),
                       url(r'^api-auth/', include('rest_framework.urls',
                                                  namespace='rest_framework')),
                       url(r'^api-token-auth/', obtain_auth_token)
                       )
