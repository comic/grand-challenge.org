import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model

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
def test_deactivate_users(settings, django_capture_on_commit_callbacks):
    settings.LAMBDA_TASKS_EAGER = True

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


@pytest.mark.django_db
def test_create_manual_verification_admin_action(settings):
    """Admin action creates a verification using the user's current email."""
    from grandchallenge.profiles.admin import create_manual_verification
    from grandchallenge.verifications.models import Verification

    user = UserFactory(email="user@example.org")
    EmailAddress.objects.create(
        user=user, email="user@example.org", verified=True
    )

    create_manual_verification(
        None,
        None,
        get_user_model().objects.filter(pk=user.pk),
    )

    verification = Verification.objects.get(user=user)
    assert verification.email == "user@example.org"
    assert verification.email_is_verified is True
    assert verification.is_verified is None
    assert verification.verified_at is None


@pytest.mark.django_db
def test_create_manual_verification_skips_existing(settings):
    """Admin action skips users who already have a verification."""
    from grandchallenge.profiles.admin import create_manual_verification
    from grandchallenge.verifications.models import Verification

    user = UserFactory(email="user@example.org")
    VerificationFactory(user=user, email="old@example.org")

    create_manual_verification(
        None,
        None,
        get_user_model().objects.filter(pk=user.pk),
    )

    # Should not have changed the existing verification
    verification = Verification.objects.get(user=user)
    assert verification.email == "old@example.org"


@pytest.mark.django_db
def test_create_manual_verification_allows_site_domain(settings):
    """Manual verification bypasses the site domain restriction."""
    from grandchallenge.profiles.admin import create_manual_verification
    from grandchallenge.verifications.models import Verification

    site_domain = settings.SESSION_COOKIE_DOMAIN.lstrip(".")
    user = UserFactory(email=f"admin@{site_domain}")

    create_manual_verification(
        None,
        None,
        get_user_model().objects.filter(pk=user.pk),
    )

    verification = Verification.objects.get(user=user)
    assert verification.email == f"admin@{site_domain}"
    assert verification.is_verified is None


@pytest.mark.django_db
def test_create_manual_verification_allows_free_email(settings):
    """Manual verification bypasses the is_free restriction."""
    from grandchallenge.profiles.admin import create_manual_verification
    from grandchallenge.verifications.models import Verification

    user = UserFactory(email="user@gmail.com")

    create_manual_verification(
        None,
        None,
        get_user_model().objects.filter(pk=user.pk),
    )

    verification = Verification.objects.get(user=user)
    assert verification.email == "user@gmail.com"
    assert verification.is_verified is None
