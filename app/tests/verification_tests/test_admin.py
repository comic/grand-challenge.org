import pytest

from grandchallenge.core.models import RequestBase
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
)
from grandchallenge.verifications.admin import (
    deactivate_vus_users,
    mark_verified,
)
from grandchallenge.verifications.models import (
    Verification,
    VerificationUserSet,
)
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmPermissionRequestFactory,
)
from tests.archives_tests.factories import (
    ArchiveFactory,
    ArchivePermissionRequestFactory,
)
from tests.factories import (
    ChallengeFactory,
    RegistrationRequestFactory,
    UserFactory,
)
from tests.reader_studies_tests.factories import (
    ReaderStudyFactory,
    ReaderStudyPermissionRequestFactory,
)
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


@pytest.mark.django_db
@pytest.mark.parametrize(
    "perm_request_factory, perm_request_entity_attr, entity_factory",
    [
        (AlgorithmPermissionRequestFactory, "algorithm", AlgorithmFactory),
        (ArchivePermissionRequestFactory, "archive", ArchiveFactory),
        (
            ReaderStudyPermissionRequestFactory,
            "reader_study",
            ReaderStudyFactory,
        ),
        (RegistrationRequestFactory, "challenge", ChallengeFactory),
    ],
)
@pytest.mark.parametrize(
    "access_request_handling, expected_request_status_without_verification, expected_request_status_with_verification",
    [
        (
            AccessRequestHandlingOptions.ACCEPT_ALL,
            RequestBase.ACCEPTED,
            RequestBase.ACCEPTED,
        ),
        (
            AccessRequestHandlingOptions.ACCEPT_VERIFIED_USERS,
            RequestBase.PENDING,
            RequestBase.ACCEPTED,
        ),
        (
            AccessRequestHandlingOptions.MANUAL_REVIEW,
            RequestBase.PENDING,
            RequestBase.PENDING,
        ),
    ],
)
def test_verify_users_and_accept_pending_requests(
    perm_request_factory,
    perm_request_entity_attr,
    entity_factory,
    access_request_handling,
    expected_request_status_without_verification,
    expected_request_status_with_verification,
):
    usr = UserFactory()

    t = entity_factory(access_request_handling=access_request_handling)
    pr = perm_request_factory(**{"user": usr, perm_request_entity_attr: t})

    VerificationFactory(user=usr, email_is_verified=True, is_verified=False)

    assert pr.status == expected_request_status_without_verification

    mark_verified(
        None,
        None,
        Verification.objects.filter(user_id=usr.pk),
    )

    pr.refresh_from_db()

    assert pr.status == expected_request_status_with_verification
