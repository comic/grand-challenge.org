import pytest
from django.conf import settings
from django.http import Http404

from grandchallenge.workstations.models import Session
from grandchallenge.workstations.utils import (
    get_or_create_active_session,
    get_workstation_image_or_404,
)
from tests.factories import (
    UserFactory,
    WorkstationFactory,
    WorkstationImageFactory,
)


@pytest.mark.django_db
def test_get_or_create_active_session():
    user = UserFactory()
    wsi = WorkstationImageFactory()

    assert Session.objects.all().count() == 0

    s = get_or_create_active_session(user=user, workstation_image=wsi)

    assert s.workstation_image == wsi
    assert s.creator == user
    assert Session.objects.all().count() == 1

    # Same workstation image and user
    s_1 = get_or_create_active_session(user=user, workstation_image=wsi)
    assert s == s_1

    # Different workstation image, same user
    wsi_1 = WorkstationImageFactory()
    s_2 = get_or_create_active_session(user=user, workstation_image=wsi_1)

    assert s_2.workstation_image == wsi_1
    assert s_2.creator == user
    assert Session.objects.all().count() == 2
    assert s_1 != s_2

    # Same workstation image, different user
    user_1 = UserFactory()
    s_3 = get_or_create_active_session(user=user_1, workstation_image=wsi)
    assert s_3.workstation_image == wsi
    assert s_3.creator == user_1
    assert Session.objects.all().count() == 3

    # Stop the original session, original workstation image and user
    s.status = s.STOPPED
    s.save()

    s_4 = get_or_create_active_session(user=user, workstation_image=wsi)
    assert s_4.workstation_image == wsi
    assert s_4.creator == user
    assert Session.objects.all().count() == 4


@pytest.mark.django_db
def test_get_workstation_image_or_404():
    # No default workstation
    with pytest.raises(Http404):
        get_workstation_image_or_404()

    default_wsi = WorkstationImageFactory(
        workstation__title=settings.DEFAULT_WORKSTATION_SLUG, ready=True
    )
    wsi = WorkstationImageFactory(ready=True)

    found_wsi = get_workstation_image_or_404()
    assert found_wsi == default_wsi

    found_wsi = get_workstation_image_or_404(slug=wsi.workstation.slug)
    assert found_wsi == wsi

    found_wsi = get_workstation_image_or_404(pk=wsi.pk)
    assert found_wsi == wsi

    # No images for workstation
    with pytest.raises(Http404):
        get_workstation_image_or_404(slug=WorkstationFactory().slug)

    # Incorrect pk
    with pytest.raises(Http404):
        get_workstation_image_or_404(pk=WorkstationFactory().pk)
