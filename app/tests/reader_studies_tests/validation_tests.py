import pytest

from grandchallenge.core.validators import JSONSchemaValidator
from grandchallenge.reader_studies.models import (
    HANGING_LIST_SCHEMA,
    Question,
)
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory
from tests.utils import get_view_for_user


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
def test_hanging_list_validation(hanging_list, expected):
    assert (
        JSONSchemaValidator(schema=HANGING_LIST_SCHEMA)(hanging_list) is None
    )

    rs = ReaderStudyFactory(hanging_list=hanging_list)
    images = [ImageFactory(name=f"image_{n}") for n in range(4)]
    rs.images.set(images)
    rs.save()

    assert rs.images.all().count() == 4

    assert rs.hanging_list_valid == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "image_names, expected",
    (
        (["1", "2"], []),
        (["1", "1", "2", "1"], ["1"]),
        (["1", "2", "1", "2", "1", "2"], ["1", "2"]),
    ),
)
def test_non_unique_images(image_names, expected):
    rs = ReaderStudyFactory()
    images = [ImageFactory(name=name) for name in image_names]
    rs.images.set(images)
    rs.save()
    assert rs.non_unique_study_image_names == expected


@pytest.mark.django_db
def test_hanging_list_shuffle_per_user(client):
    hanging_list = [{"main": f"image_{n}"} for n in range(10)]

    rs = ReaderStudyFactory(hanging_list=hanging_list)
    images = [ImageFactory(name=f"image_{n}") for n in range(10)]
    rs.images.set(images)
    rs.save()

    # The shuffling is seeded with the users pk, so needs to stay constant
    u1, u2 = UserFactory(pk=1_000_000), UserFactory(pk=1_000_001)

    rs.add_reader(user=u1)
    rs.add_reader(user=u2)

    assert rs.get_hanging_list_images_for_user(
        user=u1
    ) == rs.get_hanging_list_images_for_user(user=u2)

    rs.shuffle_hanging_list = True
    rs.save()

    u1_list = rs.get_hanging_list_images_for_user(user=u1)
    u2_list = rs.get_hanging_list_images_for_user(user=u2)

    # Check that the list is different per user and contains all of the images
    assert u1_list != u2_list
    assert (
        {u["main"] for u in u1_list}
        == {u["main"] for u in u2_list}
        == {im.api_url for im in images}
    )

    # Check that repeat requests return the same list
    assert rs.get_hanging_list_images_for_user(
        user=u1
    ) == rs.get_hanging_list_images_for_user(user=u1)

    # Check that the list is consistent over time, if not, maybe numpy has
    # changed their implementation
    api_to_image = {im.api_url: im.name for im in images}
    assert [api_to_image[h["main"]] for h in u1_list] == [
        "image_8",
        "image_3",
        "image_7",
        "image_1",
        "image_4",
        "image_9",
        "image_0",
        "image_5",
        "image_6",
        "image_2",
    ]

    # Check that the api is hooked up
    response = get_view_for_user(
        client=client,
        viewname="api:reader-study-detail",
        reverse_kwargs={"pk": rs.pk},
        user=u1,
    )
    assert response.status_code == 200
    assert response.json()["hanging_list_images"] == u1_list


ANSWER_TYPE_NAMES_AND_ANSWERS = {
    "STXT": "string test",
    "MTXT": "multiline string\ntest",
    "BOOL": True,
    "2DBB": {
        "version": {"major": 1, "minor": 0},
        "type": "2D bounding box",
        "name": "test_name",
        "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 0, 0]],
    },
    "DIST": {
        "version": {"major": 1, "minor": 0},
        "type": "Distance measurement",
        "name": "test_name",
        "start": [0, 0, 0],
        "end": [10, 0, 0],
    },
    "MDIS": {
        "version": {"major": 1, "minor": 0},
        "type": "Multiple distance measurements",
        "name": "test_name",
        "lines": [
            {
                "type": "object",
                "name": "segment1",
                "start": [0, 0, 0],
                "end": [10, 0, 0],
            },
            {"start": [0, 0, 0], "end": [10, 0, 0]},
        ],
    },
}


@pytest.mark.parametrize(
    "answer_type, answer", ANSWER_TYPE_NAMES_AND_ANSWERS.items()
)
def test_answer_type_annotation_schema(answer, answer_type):
    q = Question(answer_type=answer_type)
    assert q.is_answer_valid(answer=answer) is True


@pytest.mark.parametrize("answer", ANSWER_TYPE_NAMES_AND_ANSWERS.values())
def test_answer_type_annotation_header_schema_fails(
    answer, answer_type: str = "HEAD"
):
    q = Question(answer_type=answer_type)
    assert not q.is_answer_valid(answer=answer)


@pytest.mark.parametrize(
    "answer_type, answer_type_check",
    [
        ("STXT", "2DBB"),
        ("STXT", "DIST"),
        ("MTXT", "MDIS"),
        ("BOOL", "2DBB"),
        ("BOOL", "STXT"),
        ("2DBB", "DIST"),
        ("2DBB", "STXT"),
        ("DIST", "MDIS"),
        ("DIST", "2DBB"),
        ("MDIS", "2DBB"),
        ("MDIS", "DIST"),
    ],
)
def test_answer_type_annotation_schema_mismatch(
    answer_type, answer_type_check
):
    a = ANSWER_TYPE_NAMES_AND_ANSWERS[answer_type]
    assert Question(answer_type=answer_type).is_answer_valid(answer=a) is True
    assert (
        Question(answer_type=answer_type_check).is_answer_valid(answer=a)
        is False
    )


def test_new_answer_type_listed():
    q = Question(answer_type="TEST")
    with pytest.raises(RuntimeError):
        q.is_answer_valid(answer="foo")
