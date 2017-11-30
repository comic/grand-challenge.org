from urllib.parse import urlparse

import pytest
from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory
from django.views.generic import View

from comicmodels.models import ComicSite
from comicsite.permissions.mixins import UserIsChallengeAdminMixin, \
    UserIsChallengeParticipantOrAdminMixin
from tests.factories import ChallengeFactory, UserFactory


class EmptyResponseView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse()


class AdminOnlyView(UserIsChallengeAdminMixin, EmptyResponseView):
    pass


class ParticipantOrAdminOnlyView(UserIsChallengeParticipantOrAdminMixin,
                                 EmptyResponseView):
    pass


def assert_status(code: int, user: User, view: View, challenge: ComicSite,
                  rf: RequestFactory):
    request = rf.get('/rand')
    request.projectname = challenge.short_name

    if user is not None:
        request.user = user

    view = view.as_view()
    response = view(request)

    assert response.status_code == code
    return response


def assert_redirect(uri: str, *args):
    response = assert_status(302, *args)
    redirect_url = list(urlparse(response.url))[2]
    assert uri == redirect_url


@pytest.mark.django_db
def test_permissions_mixin(rf: RequestFactory, admin_user):
    # admin_user is a superuser, not a challenge admin
    creator = UserFactory()
    challenge = ChallengeFactory(creator=creator)
    assert challenge.is_admin(creator) == True
    assert challenge.is_participant(creator) == False

    participant = UserFactory()
    challenge.add_participant(participant)
    assert challenge.is_admin(participant) == False
    assert challenge.is_participant(participant) == True

    non_participant = UserFactory()
    assert challenge.is_admin(non_participant) == False
    assert challenge.is_participant(non_participant) == False

    assert_status(200, admin_user, AdminOnlyView, challenge, rf)
    assert_status(200, creator, AdminOnlyView, challenge, rf)
    assert_status(403, participant, AdminOnlyView, challenge, rf)
    assert_status(403, non_participant, AdminOnlyView, challenge, rf)
    assert_redirect(settings.LOGIN_URL, AnonymousUser(), AdminOnlyView,
                    challenge, rf)

    assert_status(200, admin_user, ParticipantOrAdminOnlyView, challenge, rf)
    assert_status(200, creator, ParticipantOrAdminOnlyView, challenge, rf)
    assert_status(200, participant, ParticipantOrAdminOnlyView, challenge, rf)
    assert_status(403, non_participant, ParticipantOrAdminOnlyView, challenge,
                  rf)
    assert_redirect(settings.LOGIN_URL, AnonymousUser(),
                    ParticipantOrAdminOnlyView, challenge, rf)

    # Make a 2nd challenge and make sure that the admins and participants
    # here cannot see the first
    creator2 = UserFactory()
    challenge2 = ChallengeFactory(creator=creator2)
    participant2 = UserFactory()
    challenge2.add_participant(participant2)

    assert_status(403, creator2, AdminOnlyView, challenge, rf)
    assert_status(403, participant2, AdminOnlyView, challenge, rf)

    assert_status(403, creator2, ParticipantOrAdminOnlyView, challenge, rf)
    assert_status(403, participant2, ParticipantOrAdminOnlyView, challenge, rf)
