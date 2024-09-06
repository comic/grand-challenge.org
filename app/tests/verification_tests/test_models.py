import pytest
from django.core import mail

from grandchallenge.core.models import RequestBase
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
)
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmPermissionRequestFactory,
)
from tests.archives_tests.factories import (
    ArchiveFactory,
    ArchivePermissionRequestFactory,
)
from tests.factories import UserFactory
from tests.reader_studies_tests.factories import (
    ReaderStudyFactory,
    ReaderStudyPermissionRequestFactory,
)
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
def test_email_sent_to_correct_email():
    user = UserFactory(email="personal@example.org")
    VerificationFactory(email="institutional@example.org", user=user)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["institutional@example.org"]
    assert (
        mail.outbox[0].subject
        == "[testserver] Please confirm your email address for account validation"
    )


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
def test_handling_permission_requests_on_verification(
    perm_request_factory,
    perm_request_entity_attr,
    entity_factory,
    access_request_handling,
    expected_request_status_without_verification,
    expected_request_status_with_verification,
):
    u = UserFactory()
    t = entity_factory(access_request_handling=access_request_handling)
    pr = perm_request_factory(**{"user": u, perm_request_entity_attr: t})

    v = VerificationFactory(user=u, email_is_verified=True, is_verified=False)

    assert pr.status == expected_request_status_without_verification

    v.is_verified = True
    v.save()
    pr.refresh_from_db()

    assert pr.status == expected_request_status_with_verification
