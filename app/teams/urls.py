from django.conf.urls import url

from teams.views import TeamList, TeamDetail, TeamUpdate, TeamCreate, \
    TeamMemberCreate, TeamMemberDelete

urlpatterns = [
    url(r'^$', TeamList.as_view(), name='list'),
    url(r'^create-team/$', TeamCreate.as_view(), name='create'),
    url(r'^(?P<pk>[0-9]+)/$', TeamDetail.as_view(), name='detail'),
    url(r'^(?P<pk>[0-9]+)/update/$', TeamUpdate.as_view(), name='update'),

    url(r'^(?P<pk>[0-9]+)/create-member/$', TeamMemberCreate.as_view(),
        name='member-create'),
    url(r'^m/(?P<pk>[0-9]+)/delete/$',
        TeamMemberDelete.as_view(), name='member-delete'),
]
