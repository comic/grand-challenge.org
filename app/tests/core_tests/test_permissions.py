import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory
from django.views.generic import View
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)

from grandchallenge.teams.permissions.mixins import (
    UserIsChallengeParticipantOrAdminMixin,
)
from tests.factories import ChallengeFactory, UserFactory
from tests.utils import assert_redirect, assert_status


class EmptyResponseView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse()


class AdminOnlyView(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, EmptyResponseView
):
    permission_required = "change_challenge"
    raise_exception = True

    def get_permission_object(self):
        return self.request.challenge

    pass


class ParticipantOrAdminOnlyView(
    UserIsChallengeParticipantOrAdminMixin, EmptyResponseView
):
    pass


@pytest.mark.django_db
def test_permissions_mixin(
    rf: RequestFactory, admin_user, mocker, challenge_set
):
    # admin_user is a superuser, not a challenge admin
    creator = challenge_set.creator
    challenge = challenge_set.challenge
    participant = challenge_set.participant
    non_participant = challenge_set.non_participant

    # Messages need to be mocked when using request factory
    mock_messages = mocker.patch(
        "grandchallenge.core.permissions.mixins.messages"
    ).start()

    mock_messages.INFO = "INFO"
    assert_status(200, admin_user, AdminOnlyView, challenge, rf)
    assert_status(200, creator, AdminOnlyView, challenge, rf)
    assert_status(403, participant, AdminOnlyView, challenge, rf)
    assert_status(403, non_participant, AdminOnlyView, challenge, rf)
    assert_redirect(
        settings.LOGIN_URL, AnonymousUser(), AdminOnlyView, challenge, rf
    )
    assert_status(200, admin_user, ParticipantOrAdminOnlyView, challenge, rf)
    assert_status(200, creator, ParticipantOrAdminOnlyView, challenge, rf)
    assert_status(200, participant, ParticipantOrAdminOnlyView, challenge, rf)
    assert_status(
        403, non_participant, ParticipantOrAdminOnlyView, challenge, rf
    )
    assert_redirect(
        settings.LOGIN_URL,
        AnonymousUser(),
        ParticipantOrAdminOnlyView,
        challenge,
        rf,
    )
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


@pytest.mark.django_db
def test_permissions_after_challenge_rename(
    rf: RequestFactory, admin_user, mocker, challenge_set
):
    """
    Check that we can rename challenges.

    admin_user is superuser.
    """
    creator = challenge_set.creator
    challenge = challenge_set.challenge
    participant = challenge_set.participant
    non_participant = challenge_set.non_participant
    # Messages need to be mocked when using request factory
    mock_messages = mocker.patch(
        "grandchallenge.core.permissions.mixins.messages"
    ).start()
    mock_messages.INFO = "INFO"
    assert_status(200, admin_user, AdminOnlyView, challenge, rf)
    assert_status(200, creator, AdminOnlyView, challenge, rf)
    assert_status(403, participant, AdminOnlyView, challenge, rf)
    assert_status(403, non_participant, AdminOnlyView, challenge, rf)
    assert_redirect(
        settings.LOGIN_URL, AnonymousUser(), AdminOnlyView, challenge, rf
    )
    assert_status(200, admin_user, ParticipantOrAdminOnlyView, challenge, rf)
    assert_status(200, creator, ParticipantOrAdminOnlyView, challenge, rf)
    assert_status(200, participant, ParticipantOrAdminOnlyView, challenge, rf)
    assert_status(
        403, non_participant, ParticipantOrAdminOnlyView, challenge, rf
    )
    assert_redirect(
        settings.LOGIN_URL,
        AnonymousUser(),
        ParticipantOrAdminOnlyView,
        challenge,
        rf,
    )
    challenge.short_name += "appendedname"
    challenge.save()
    assert_status(200, admin_user, AdminOnlyView, challenge, rf)
    assert_status(200, creator, AdminOnlyView, challenge, rf)
    assert_status(403, participant, AdminOnlyView, challenge, rf)
    assert_status(403, non_participant, AdminOnlyView, challenge, rf)
    assert_redirect(
        settings.LOGIN_URL, AnonymousUser(), AdminOnlyView, challenge, rf
    )
    assert_status(200, admin_user, ParticipantOrAdminOnlyView, challenge, rf)
    assert_status(200, creator, ParticipantOrAdminOnlyView, challenge, rf)
    assert_status(200, participant, ParticipantOrAdminOnlyView, challenge, rf)
    assert_status(
        403, non_participant, ParticipantOrAdminOnlyView, challenge, rf
    )
    assert_redirect(
        settings.LOGIN_URL,
        AnonymousUser(),
        ParticipantOrAdminOnlyView,
        challenge,
        rf,
    )
