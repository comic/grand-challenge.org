from django.conf.urls import url

from challenges.views import ChallengeCreate, ChallengeList

urlpatterns = [
    url(r'^my-challenges/$', ChallengeList.as_view(), name='list'),
    url(r'^create/$', ChallengeCreate.as_view(), name='create'),
]
