import pytest

from grandchallenge.reader_studies.tasks import add_images_to_reader_study
from tests.factories import ImageFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory


@pytest.mark.django_db
def test_add_images_is_idempotent():
    rs = ReaderStudyFactory()
    image = ImageFactory()

    assert rs.civs.count() == 0

    add_images_to_reader_study(
        upload_session_pk=image.origin.pk, reader_study_pk=rs.pk
    )

    assert rs.civs.count() == 1

    add_images_to_reader_study(
        upload_session_pk=image.origin.pk, reader_study_pk=rs.pk
    )

    assert rs.civs.count() == 1
