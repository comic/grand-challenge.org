import pytest

from grandchallenge.components.models import ComponentInterface
from grandchallenge.reader_studies.tasks import (
    add_images_to_reader_study,
    create_display_sets_for_upload_session,
)
from tests.factories import ImageFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory


@pytest.mark.django_db
def test_add_images_is_idempotent():
    rs = ReaderStudyFactory(use_display_sets=False)
    image = ImageFactory()

    assert rs.images.count() == 0

    add_images_to_reader_study(
        upload_session_pk=image.origin.pk, reader_study_pk=rs.pk
    )

    assert rs.images.count() == 1

    add_images_to_reader_study(
        upload_session_pk=image.origin.pk, reader_study_pk=rs.pk
    )

    assert rs.images.count() == 1


@pytest.mark.django_db
def test_create_display_sets_for_upload_session():
    rs = ReaderStudyFactory(use_display_sets=False)
    image = ImageFactory()
    ci = ComponentInterface.objects.get(slug="generic-medical-image")

    assert rs.images.count() == 0

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
