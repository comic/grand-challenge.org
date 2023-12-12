import pytest

from grandchallenge.verifications.admin import deactivate_vus_users
from grandchallenge.verifications.models import VerificationUserSet
from tests.factories import UserFactory
from tests.verification_tests.factories import (
    VerificationFactory,
    VerificationUserSetFactory,
)


@pytest.mark.django_db
def test_deactivate_users(django_capture_on_commit_callbacks, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    users = UserFactory.create_batch(5)

    vus = VerificationUserSetFactory.create_batch(4)

    VerificationFactory(user=users[0], is_verified=True)
    VerificationFactory(user=users[1])
    VerificationFactory(user=users[3], is_verified=True)

    # These two are selected, should be deactivated
    vus[0].users.set([users[0], users[1]])
    vus[1].users.set([users[2]])

    # Not selected, but contains joint member, should be deactivated
    vus[2].users.set([users[0]])

    # Not selected, should not be deactivated
    vus[3].users.set([users[3]])

    # user[4] not part of a verification factory

    with django_capture_on_commit_callbacks(execute=True):
        deactivate_vus_users(
            None,
            None,
            VerificationUserSet.objects.filter(pk__in=[vus[0].pk, vus[1].pk]),
        )

    for user in users:
        user.refresh_from_db()

    assert users[0].is_active is False
    assert users[0].verification.is_verified is False
    assert users[1].is_active is False
    assert users[1].verification.is_verified is False
    assert users[2].is_active is False
    assert users[3].is_active is True
    assert users[3].verification.is_verified is True
    assert users[4].is_active is True
