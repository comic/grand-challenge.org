from django.conf.urls import url

from challenges.views import ChallengeCreate

urlpatterns = [
    url(r'^create/$', ChallengeCreate.as_view(), name='create'),
]
