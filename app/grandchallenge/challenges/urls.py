from django.conf.urls import url

from grandchallenge.challenges.views import (
    ChallengeCreate, ChallengeList, ChallengeUpdate,
)

urlpatterns = [
    url(r'^my-challenges/$', ChallengeList.as_view(), name='list'),
    url(r'^create/$', ChallengeCreate.as_view(), name='create'),
    url(
        r'^(?P<challenge_short_name>[\w-]+)/update/$',
        ChallengeUpdate.as_view(),
        name='update',
    ),
]
