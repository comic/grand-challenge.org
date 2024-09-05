import pytest

from grandchallenge.verifications.models import VerificationUserSet
from tests.factories import UserFactory


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
