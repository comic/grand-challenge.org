import pytest

from grandchallenge.core.validators import JSONSchemaValidator
from grandchallenge.reader_studies.models import HANGING_LIST_SCHEMA
from tests.factories import ImageFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "hanging_list,expected",
    (
        ([], False),
        # Missing images
        ([{"main": "image_0", "secondary": "image_1"}], False),
        # Unknown images
        (
            [
                {"main": "image_0", "secondary": "image_1"},
                {"main": "image_2", "secondary": "image_3"},
                {"main": "image_4", "secondary": "image_5"},
            ],
            False,
        ),
        # Duplicated images
        (
            [
                {"main": "image_0", "secondary": "image_1"},
                {"main": "image_2", "secondary": "image_3"},
                {"main": "image_0"},
            ],
            False,
        ),
        # Everything is good
        (
            [
                {"main": "image_0", "secondary": "image_1"},
                {"main": "image_2", "secondary": "image_3"},
            ],
            True,
        ),
    ),
)
def test_validation(hanging_list, expected):
    assert (
        JSONSchemaValidator(schema=HANGING_LIST_SCHEMA)(hanging_list) is None
    )

    rs = ReaderStudyFactory(hanging_list=hanging_list)
    images = [ImageFactory(name=f"image_{n}") for n in range(4)]
    rs.images.set(images)
    rs.save()

    assert rs.images.all().count() == 4

    assert rs.hanging_list_valid == expected
