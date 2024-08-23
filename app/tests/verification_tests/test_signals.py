import pytest

from grandchallenge.algorithms.models import AlgorithmPermissionRequest
from grandchallenge.verifications.models import VerificationUserSet
from tests.algorithms_tests.factories import AlgorithmPermissionRequestFactory
from tests.factories import UserFactory
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
def test_auto_accept_permission_on_verification():
    u = UserFactory()
    alpr = AlgorithmPermissionRequestFactory(user=u)

    assert alpr.status == AlgorithmPermissionRequest.PENDING

    v = VerificationFactory(user=u, email_is_verified=True, is_verified=False)
    v.is_verified = True
    v.save()
    alpr.refresh_from_db()

    assert alpr.status == AlgorithmPermissionRequest.ACCEPTED
