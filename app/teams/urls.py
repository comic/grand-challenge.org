from django.conf.urls import url

from teams.views import TeamList, TeamDetail, TeamUpdate, TeamCreate

urlpatterns = [
    url(r'^$', TeamList.as_view(), name='list'),
    url(r'^create/$', TeamCreate.as_view(), name='create'),
    url(r'^(?P<pk>[0-9]+)/$', TeamDetail.as_view(), name='detail'),
    url(r'^(?P<pk>[0-9]+)/update/$', TeamUpdate.as_view(), name='update'),
]
