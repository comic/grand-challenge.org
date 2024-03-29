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
