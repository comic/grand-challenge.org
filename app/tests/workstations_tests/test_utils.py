import pytest

from grandchallenge.workstations.models import Session
from grandchallenge.workstations.utils import get_or_create_active_session
from tests.factories import UserFactory, WorkstationImageFactory


@pytest.mark.django_db
def test_get_or_create_active_session():
    user = UserFactory()
    wsi = WorkstationImageFactory()

    assert Session.objects.all().count() == 0

    s = get_or_create_active_session(
        user=user, workstation_image=wsi, region="eu-central-1"
    )

    assert s.workstation_image == wsi
    assert s.creator == user
    assert Session.objects.all().count() == 1

    # Same workstation image and user
    s_1 = get_or_create_active_session(
        user=user, workstation_image=wsi, region="eu-central-1"
    )
    assert s == s_1

    # Different workstation image, same user
    wsi_1 = WorkstationImageFactory()
    s_2 = get_or_create_active_session(
        user=user, workstation_image=wsi_1, region="eu-central-1"
    )

    assert s_2.workstation_image == wsi_1
    assert s_2.creator == user
    assert Session.objects.all().count() == 2
    assert s_1 != s_2

    # Same workstation image, different user
    user_1 = UserFactory()
    s_3 = get_or_create_active_session(
        user=user_1, workstation_image=wsi, region="eu-central-1"
    )
    assert s_3.workstation_image == wsi
    assert s_3.creator == user_1
    assert Session.objects.all().count() == 3

    # Stop the original session, original workstation image and user
    s.status = s.STOPPED
    s.save()

    s_4 = get_or_create_active_session(
        user=user, workstation_image=wsi, region="eu-central-1"
    )
    assert s_4.workstation_image == wsi
    assert s_4.creator == user
    assert Session.objects.all().count() == 4


@pytest.mark.django_db
def test_unclaimed_session_is_claimed():
    user = UserFactory()
    wsi = WorkstationImageFactory()
    unclaimed = Session.objects.create(
        creator=None, workstation_image=wsi, region="eu-central-1"
    )

    s = get_or_create_active_session(
        user=user, workstation_image=wsi, region="eu-central-1"
    )

    assert s.pk == unclaimed.pk
    assert s.creator == user
    assert s.claimed_at is not None
    assert Session.objects.count() == 1


@pytest.mark.django_db
def test_unclaimed_session_not_claimed_with_extra_env_vars():
    user = UserFactory()
    wsi = WorkstationImageFactory()
    Session.objects.create(
        creator=None, workstation_image=wsi, region="eu-central-1"
    )

    s = get_or_create_active_session(
        user=user,
        workstation_image=wsi,
        region="eu-central-1",
        extra_env_vars=[{"name": "FOO", "value": "bar"}],
    )

    assert s.creator == user
    assert s.extra_env_vars == [{"name": "FOO", "value": "bar"}]
    assert Session.objects.count() == 2


@pytest.mark.django_db
def test_unclaimed_session_not_claimed_wrong_region():
    user = UserFactory()
    wsi = WorkstationImageFactory()
    Session.objects.create(
        creator=None, workstation_image=wsi, region="us-east-1"
    )

    s = get_or_create_active_session(
        user=user, workstation_image=wsi, region="eu-central-1"
    )

    assert s.creator == user
    assert Session.objects.count() == 2


@pytest.mark.django_db
def test_unclaimed_session_not_claimed_wrong_workstation_image():
    user = UserFactory()
    wsi = WorkstationImageFactory()
    other_wsi = WorkstationImageFactory()
    Session.objects.create(
        creator=None, workstation_image=other_wsi, region="eu-central-1"
    )

    s = get_or_create_active_session(
        user=user, workstation_image=wsi, region="eu-central-1"
    )

    assert s.creator == user
    assert s.workstation_image == wsi
    assert Session.objects.count() == 2


@pytest.mark.django_db
def test_unclaimed_session_ping_times_set_on_claim():
    user = UserFactory()
    wsi = WorkstationImageFactory()
    unclaimed = Session.objects.create(
        creator=None, workstation_image=wsi, region="eu-central-1"
    )

    ping_times = {"eu-central-1": 10, "us-east-1": 100}
    s = get_or_create_active_session(
        user=user,
        workstation_image=wsi,
        region="eu-central-1",
        ping_times=ping_times,
    )

    assert s.pk == unclaimed.pk
    assert s.ping_times == ping_times


@pytest.mark.django_db
def test_existing_session_preferred_over_unclaimed():
    user = UserFactory()
    wsi = WorkstationImageFactory()
    Session.objects.create(
        creator=None, workstation_image=wsi, region="eu-central-1"
    )
    existing = Session.objects.create(
        creator=user, workstation_image=wsi, region="eu-central-1"
    )

    s = get_or_create_active_session(
        user=user, workstation_image=wsi, region="eu-central-1"
    )

    assert s.pk == existing.pk
    assert Session.objects.count() == 2


@pytest.mark.django_db
def test_stopped_unclaimed_session_not_claimed():
    user = UserFactory()
    wsi = WorkstationImageFactory()
    unclaimed = Session.objects.create(
        creator=None, workstation_image=wsi, region="eu-central-1"
    )
    Session.objects.filter(pk=unclaimed.pk).update(status=Session.STOPPED)

    s = get_or_create_active_session(
        user=user, workstation_image=wsi, region="eu-central-1"
    )

    assert s.pk != unclaimed.pk
    assert s.creator == user
    assert Session.objects.count() == 2
