import pytest

from grandchallenge.core.models import RequestBase
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
)
from grandchallenge.verifications.models import VerificationUserSet
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
@pytest.mark.parametrize(
    "auto_deactivate",
    (True, False),
)
def test_auto_deactivate(
    auto_deactivate, django_capture_on_commit_callbacks, settings
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    vus = VerificationUserSet.objects.create(auto_deactivate=auto_deactivate)
    u = UserFactory()

    with django_capture_on_commit_callbacks(execute=True):
        vus.users.add(u)

    u.refresh_from_db()

    assert u.is_active is not auto_deactivate


@pytest.mark.django_db
@pytest.mark.parametrize(
    "auto_deactivate",
    (True, False),
)
def test_auto_deactivate_reverse(
    auto_deactivate, django_capture_on_commit_callbacks, settings
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    vus = VerificationUserSet.objects.create(auto_deactivate=auto_deactivate)
    u = UserFactory()

    with django_capture_on_commit_callbacks(execute=True):
        u.verificationuserset_set.add(vus)

    u.refresh_from_db()

    assert u.is_active is not auto_deactivate


@pytest.mark.django_db
@pytest.mark.parametrize(
    "auto_deactivate",
    (True, False),
)
def test_auto_deactivate_set(
    auto_deactivate, django_capture_on_commit_callbacks, settings
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    vus = VerificationUserSet.objects.create(auto_deactivate=auto_deactivate)
    u = UserFactory()

    with django_capture_on_commit_callbacks(execute=True):
        vus.users.set([u])

    u.refresh_from_db()

    assert u.is_active is not auto_deactivate


@pytest.mark.django_db
@pytest.mark.parametrize(
    "auto_deactivate",
    (True, False),
)
def test_auto_deactivate_reverse_set(
    auto_deactivate, django_capture_on_commit_callbacks, settings
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    vus = VerificationUserSet.objects.create(auto_deactivate=auto_deactivate)
    u = UserFactory()

    with django_capture_on_commit_callbacks(execute=True):
        u.verificationuserset_set.set([vus])

    u.refresh_from_db()

    assert u.is_active is not auto_deactivate


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
    "access_request_handling, verified_status, expected_status",
    [
        (AccessRequestHandlingOptions.ACCEPT_ALL, True, RequestBase.ACCEPTED),
        (AccessRequestHandlingOptions.ACCEPT_ALL, False, RequestBase.ACCEPTED),
        (
            AccessRequestHandlingOptions.ACCEPT_VERIFIED_USERS,
            True,
            RequestBase.ACCEPTED,
        ),
        (
            AccessRequestHandlingOptions.ACCEPT_VERIFIED_USERS,
            False,
            RequestBase.PENDING,
        ),
        (
            AccessRequestHandlingOptions.MANUAL_REVIEW,
            True,
            RequestBase.PENDING,
        ),
    ],
)
def test_auto_accept_permission_requests_on_verification(
    perm_request_factory,
    perm_request_entity_attr,
    entity_factory,
    access_request_handling,
    verified_status,
    expected_status,
):
    u = UserFactory()
    t = entity_factory(access_request_handling=access_request_handling)
    pr = perm_request_factory(user=u)

    setattr(pr, perm_request_entity_attr, t)
    pr.save()

    assert pr.status == RequestBase.PENDING

    VerificationFactory(
        user=u, email_is_verified=True, is_verified=verified_status
    )
    pr.refresh_from_db()

    assert pr.status == expected_status
