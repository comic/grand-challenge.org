import pytest

from grandchallenge.core.validators import JSONValidator
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
                {
                    "main": "image_2",
                    "secondary": "image_3",
                    "tertiary": "image_4",
                },
            ],
            True,
        ),
    ),
)
def test_hanging_list_validation(hanging_list, expected):
    assert JSONValidator(schema=HANGING_LIST_SCHEMA)(hanging_list) is None

    rs = ReaderStudyFactory(hanging_list=hanging_list)
    images = [ImageFactory(name=f"image_{n}") for n in range(5)]
    rs.images.set(images)
    rs.save()

    assert rs.images.all().count() == 5

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
    "NUMB": 12,
    "BOOL": True,
    "2DBB": {
        "version": {"major": 1, "minor": 0},
        "type": "2D bounding box",
        "name": "test_name",
        "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]],
        "probability": 0.2,
    },
    "M2DB": {
        "type": "Multiple 2D bounding boxes",
        "boxes": [
            {
                "name": "foo",
                "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]],
            },
            {
                "corners": [[0, 0, 0], [10, 0, 0], [10, 20, 0], [0, 20, 0]],
                "probability": 0.2,
            },
        ],
        "version": {"major": 1, "minor": 0},
    },
    "DIST": {
        "version": {"major": 1, "minor": 0},
        "type": "Distance measurement",
        "name": "test_name",
        "start": [0, 0, 0],
        "end": [10, 0, 0],
        "probability": 1.0,
    },
    "MDIS": {
        "version": {"major": 1, "minor": 0},
        "type": "Multiple distance measurements",
        "name": "test_name",
        "lines": [
            {"name": "segment1", "start": [0, 0, 0], "end": [10, 0, 0]},
            {"start": [0, 0, 0], "end": [10, 0, 0], "probability": 0.5},
        ],
    },
    "POIN": {
        "version": {"major": 1, "minor": 0},
        "type": "Point",
        "name": "test_name",
        "point": [0, 0, 0],
        "probability": 0.41,
    },
    "MPOI": {
        "version": {"major": 1, "minor": 0},
        "type": "Multiple points",
        "name": "test_name",
        "points": [
            {"point": [0, 0, 0]},
            {"point": [0, 0, 0], "probability": 0.2},
        ],
    },
    "POLY": {
        "version": {"major": 1, "minor": 0},
        "type": "Polygon",
        "name": "test_name",
        "seed_point": [0, 0, 0],
        "path_points": [[0, 0, 0], [0, 0, 0]],
        "sub_type": "poly",
        "groups": ["a", "b"],
        "probability": 0.3,
    },
    "MPOL": {
        "version": {"major": 1, "minor": 0},
        "type": "Multiple polygons",
        "name": "test_name",
        "polygons": [
            {
                "name": "test_name",
                "seed_point": [0, 0, 0],
                "path_points": [[0, 0, 0], [0, 0, 0]],
                "sub_type": "poly",
                "groups": ["a", "b"],
            },
            {
                "name": "test_name",
                "seed_point": [0, 0, 0],
                "path_points": [[0, 0, 0], [0, 0, 0]],
                "sub_type": "poly",
                "groups": ["a", "b"],
                "probability": 0.54,
            },
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


def test_answer_type_annotation_schema_mismatch():
    # Answers to STXT are valid for MTXT as well, that's why STXT is excluded
    # Other than that, each answer is only valid for a single answer type
    unique_answer_types = [
        key for key in ANSWER_TYPE_NAMES_AND_ANSWERS.keys() if key != "STXT"
    ]
    for answer_type in unique_answer_types:
        answer = ANSWER_TYPE_NAMES_AND_ANSWERS[answer_type]
        for answer_type_check in unique_answer_types:
            assert Question(answer_type=answer_type_check).is_answer_valid(
                answer=answer
            ) == (answer_type == answer_type_check)


def test_new_answer_type_listed():
    q = Question(answer_type="TEST")
    with pytest.raises(RuntimeError):
        q.is_answer_valid(answer="foo")


@pytest.mark.parametrize(
    "answer_type,allow_null",
    [
        ["STXT", False],
        ["MTXT", False],
        ["BOOL", False],
        ["NUMB", True],
        ["2DBB", True],
        ["M2DB", True],
        ["DIST", True],
        ["MDIS", True],
        ["POIN", True],
        ["MPOI", True],
        ["POLY", True],
        ["PIMG", True],
        ["MPOL", True],
        ["MPIM", True],
        ["CHOI", True],
        ["MCHO", False],
        ["MCHD", False],
        ["MASK", True],
    ],
)
def test_answer_type_allows_null(answer_type, allow_null):
    q = Question(answer_type=answer_type)
    assert q.is_answer_valid(answer=None) == allow_null
