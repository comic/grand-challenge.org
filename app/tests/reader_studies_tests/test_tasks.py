import pytest

from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.reader_studies.tasks import (
    add_image_to_display_set,
    create_display_sets_for_upload_session,
)
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.factories import ImageFactory
from tests.reader_studies_tests.factories import (
    DisplaySetFactory,
    ReaderStudyFactory,
)


@pytest.mark.django_db
def test_create_display_sets_for_upload_session():
    rs = ReaderStudyFactory()
    image = ImageFactory()
    ci = ComponentInterface.objects.get(slug="generic-medical-image")

    assert rs.display_sets.count() == 0

    create_display_sets_for_upload_session(
        upload_session_pk=image.origin.pk,
        reader_study_pk=rs.pk,
        interface_pk=ci.pk,
    )

    assert rs.display_sets.count() == 1
    assert rs.display_sets.first().values.first().image == image

    create_display_sets_for_upload_session(
        upload_session_pk=image.origin.pk,
        reader_study_pk=rs.pk,
        interface_pk=ci.pk,
    )

    assert rs.display_sets.count() == 1
    assert rs.display_sets.first().values.first().image == image


@pytest.mark.django_db
def test_add_image_to_display_set(settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    ds = DisplaySetFactory()
    us = RawImageUploadSessionFactory()
    ci = ComponentInterfaceFactory(kind="IMG")

    error_message = "Image imports should result in a single image"

    add_image_to_display_set(
        upload_session_pk=us.pk,
        display_set_pk=ds.pk,
        interface_pk=ci.pk,
    )

    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 0
    us.refresh_from_db()
    assert us.status == RawImageUploadSession.FAILURE
    assert us.error_message == error_message

    im1, im2 = ImageFactory.create_batch(2, origin=us)

    add_image_to_display_set(
        upload_session_pk=us.pk,
        display_set_pk=ds.pk,
        interface_pk=ci.pk,
    )
    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 0
    us.refresh_from_db()
    assert us.status == RawImageUploadSession.FAILURE
    assert us.error_message == error_message

    im2.delete()

    add_image_to_display_set(
        upload_session_pk=us.pk,
        display_set_pk=ds.pk,
        interface_pk=ci.pk,
    )
    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 1
