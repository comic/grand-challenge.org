import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from guardian.utils import get_anonymous_user

from grandchallenge.profiles.tasks import (
    deactivate_user,
    delete_users_who_dont_login,
)
from tests.factories import UserFactory
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
def test_delete_users_who_dont_login(settings, client):
    settings.USER_LOGIN_TIMEOUT_DAYS = 0
    anon = get_anonymous_user()
    u1, u2 = UserFactory.create_batch(2)
    # u1 logs in and should not be deleted
    client.force_login(user=u1)

    assert {*get_user_model().objects.all()} == {anon, u1, u2}

    delete_users_who_dont_login()

    assert {*get_user_model().objects.all()} == {anon, u1}

    with pytest.raises(ObjectDoesNotExist):
        # u2 did not log in so was deleted
        u2.refresh_from_db()


@pytest.mark.django_db
def test_deactivate_user(client):
    u1, u2 = UserFactory.create_batch(2)

    # Create sessions for each user
    client.force_login(u1)
    client.force_login(u2)

    # Create verifications
    VerificationFactory(user=u1, is_verified=True)
    VerificationFactory(user=u2, is_verified=True)

    deactivate_user(user_pk=u1.pk)

    u1.refresh_from_db()
    u2.refresh_from_db()

    assert u1.is_active is False
    assert u2.is_active is True
    assert u1.verification.is_verified is False
    assert u2.verification.is_verified is True
    assert u1.browser_sessions.count() == 0
    assert u2.browser_sessions.count() == 1
