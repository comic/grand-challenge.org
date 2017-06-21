from django.conf.urls import url, include, patterns

from .views import ResultList, ResultDetail

urlpatterns = patterns('',
                       url(r'^api/v1/results/$', ResultList.as_view()),
                       url(r'^api/v1/results/(?P<pk>[0-9]+)/$',
                           ResultDetail.as_view()),
                       url(r'^api-auth/', include('rest_framework.urls',
                                                  namespace='rest_framework'))
                       )
