from django.urls import path

from grandchallenge.challenges.views import (
    ChallengeCreate,
    UsersChallengeList,
    ChallengeUpdate,
    ExternalChallengeCreate,
    ExternalChallengeUpdate,
    ChallengeList,
)

app_name = 'challenges'

urlpatterns = [
    path("", ChallengeList.as_view(), name="list"),
    path('my-challenges/', UsersChallengeList.as_view(), name='users-list'),
    path('create/', ChallengeCreate.as_view(), name='create'),

    path(
        'external/create/',
        ExternalChallengeCreate.as_view(),
        name='external-create'
    ),
    path(
        "external/<slug:short_name>/",
        ExternalChallengeUpdate.as_view(),
        name="external-update",
    ),
    path(
        '<slug:challenge_short_name>/update/',
        ChallengeUpdate.as_view(),
        name='update',
    ),
]
