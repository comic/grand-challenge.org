import pytest

from grandchallenge.reader_studies.models import AnswerType, Question

ANSWER_TYPE_NAMES_AND_ANSWERS = {
    AnswerType.TEXT: "multiline string\ntest",
    AnswerType.NUMBER: 12,
    AnswerType.BOOL: True,
    AnswerType.BOUNDING_BOX_2D: {
        "version": {"major": 1, "minor": 0},
        "type": "2D bounding box",
        "name": "test_name",
        "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]],
        "probability": 0.2,
    },
    AnswerType.MULTIPLE_2D_BOUNDING_BOXES: {
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
    AnswerType.DISTANCE_MEASUREMENT: {
        "version": {"major": 1, "minor": 0},
        "type": "Distance measurement",
        "name": "test_name",
        "start": [0, 0, 0],
        "end": [10, 0, 0],
        "probability": 1.0,
    },
    AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS: {
        "version": {"major": 1, "minor": 0},
        "type": "Multiple distance measurements",
        "name": "test_name",
        "lines": [
            {"name": "segment1", "start": [0, 0, 0], "end": [10, 0, 0]},
            {"start": [0, 0, 0], "end": [10, 0, 0], "probability": 0.5},
        ],
    },
    AnswerType.POINT: {
        "version": {"major": 1, "minor": 0},
        "type": "Point",
        "name": "test_name",
        "point": [0, 0, 0],
        "probability": 0.41,
    },
    AnswerType.MULTIPLE_POINTS: {
        "version": {"major": 1, "minor": 0},
        "type": "Multiple points",
        "name": "test_name",
        "points": [
            {"point": [0, 0, 0]},
            {"point": [0, 0, 0], "probability": 0.2},
        ],
    },
    AnswerType.POLYGON: {
        "version": {"major": 1, "minor": 0},
        "type": "Polygon",
        "name": "test_name",
        "seed_point": [0, 0, 0],
        "path_points": [[0, 0, 0], [0, 0, 0]],
        "sub_type": "poly",
        "groups": ["a", "b"],
        "probability": 0.3,
    },
    AnswerType.MULTIPLE_POLYGONS: {
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
    AnswerType.LINE: {
        "version": {"major": 1, "minor": 0},
        "type": "Line",
        "name": "test_name",
        "seed_points": [[0, 0, 0], [0, 0, 0]],
        "path_point_lists": [
            [[0, 0, 0], [0, 0, 0]],
            [[1, 1, 1], [1, 1, 1]],
        ],
        "probability": 0.3,
    },
    AnswerType.MULTIPLE_LINES: {
        "version": {"major": 1, "minor": 0},
        "type": "Multiple lines",
        "name": "test_name",
        "lines": [
            {
                "name": "test_name",
                "seed_points": [[0, 0, 0], [0, 0, 0]],
                "path_point_lists": [
                    [[0, 0, 0], [0, 0, 0]],
                    [[1, 1, 1], [1, 1, 1]],
                ],
                "probability": 0.54,
            },
            {
                "name": "test_name",
                "seed_points": [[0, 0, 0], [0, 0, 0]],
                "path_point_lists": [
                    [[0, 0, 0], [0, 0, 0]],
                    [[1, 1, 1], [1, 1, 1]],
                ],
                "probability": 0.54,
            },
        ],
    },
    AnswerType.ANGLE: {
        "version": {"major": 1, "minor": 0},
        "type": "Angle",
        "name": "test_name",
        "lines": [
            [[0, 0, 0], [0, 0, 0]],
            [[1, 1, 1], [1, 1, 1]],
        ],
        "probability": 0.3,
    },
    AnswerType.MULTIPLE_ANGLES: {
        "version": {"major": 1, "minor": 0},
        "type": "Multiple angles",
        "name": "test_name",
        "angles": [
            {
                "name": "test_name",
                "lines": [
                    [[0, 0, 0], [0, 0, 0]],
                    [[1, 1, 1], [1, 1, 1]],
                ],
                "probability": 0.54,
            },
            {
                "name": "test_name",
                "lines": [
                    [[0, 0, 0], [0, 0, 0]],
                    [[1, 1, 1], [1, 1, 1]],
                ],
                "probability": 0.54,
            },
        ],
    },
    AnswerType.ELLIPSE: {
        "version": {"major": 1, "minor": 0},
        "type": "Ellipse",
        "name": "test_name",
        "major_axis": [[0, 0, 0], [0, 0, 0]],
        "minor_axis": [[1, 1, 1], [1, 1, 1]],
        "probability": 0.3,
    },
    AnswerType.MULTIPLE_ELLIPSES: {
        "version": {"major": 1, "minor": 0},
        "type": "Multiple ellipses",
        "name": "test_name",
        "ellipses": [
            {
                "name": "ellipse1",
                "major_axis": [[0, 0, 0], [0, 0, 0]],
                "minor_axis": [[1, 1, 1], [1, 1, 1]],
                "probability": 0.3,
            },
            {
                "name": "ellipse2",
                "major_axis": [[0, 0, 0], [0, 0, 0]],
                "minor_axis": [[1, 1, 1], [1, 1, 1]],
            },
        ],
    },
    AnswerType.THREE_POINT_ANGLE: {
        "version": {"major": 1, "minor": 0},
        "name": "Some annotation",
        "type": "Three-point angle",
        "angle": [
            [78.29, -17.14, 76.82],
            [76.801, -57.62, 84.43],
            [77.10, -18.97, 115.48],
        ],
        "probability": 0.92,
    },
    AnswerType.MULTIPLE_THREE_POINT_ANGLES: {
        "version": {"major": 1, "minor": 0},
        "name": "Some annotations",
        "type": "Multiple three-point angles",
        "angles": [
            {
                "name": "Annotation 1",
                "type": "Three-point angle",
                "angle": [
                    [78.29, -17.14, 76.82],
                    [76.801, -57.62, 84.43],
                    [77.10, -18.97, 115.48],
                ],
                "probability": 0.92,
            },
            {
                "name": "Annotation 2",
                "type": "Three-point angle",
                "angle": [
                    [78.29, -17.14, 76.82],
                    [76.801, -57.62, 84.43],
                    [77.10, -18.97, 115.48],
                ],
                "probability": 0.92,
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
    for answer_type in ANSWER_TYPE_NAMES_AND_ANSWERS.keys():
        answer = ANSWER_TYPE_NAMES_AND_ANSWERS[answer_type]
        for answer_type_check in ANSWER_TYPE_NAMES_AND_ANSWERS.keys():
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
        [AnswerType.TEXT, False],
        [AnswerType.BOOL, True],
        [AnswerType.NUMBER, True],
        [AnswerType.BOUNDING_BOX_2D, True],
        [AnswerType.MULTIPLE_2D_BOUNDING_BOXES, True],
        [AnswerType.DISTANCE_MEASUREMENT, True],
        [AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS, True],
        [AnswerType.POINT, True],
        [AnswerType.MULTIPLE_POINTS, True],
        [AnswerType.POLYGON, True],
        [AnswerType.MULTIPLE_POLYGONS, True],
        [AnswerType.CHOICE, True],
        [AnswerType.MULTIPLE_CHOICE, False],
        [AnswerType.MULTIPLE_CHOICE_DROPDOWN, False],
        [AnswerType.MASK, True],
        [AnswerType.LINE, True],
        [AnswerType.MULTIPLE_LINES, True],
        [AnswerType.ANGLE, True],
        [AnswerType.MULTIPLE_ANGLES, True],
        [AnswerType.ELLIPSE, True],
        [AnswerType.MULTIPLE_ELLIPSES, True],
        [AnswerType.THREE_POINT_ANGLE, True],
        [AnswerType.MULTIPLE_THREE_POINT_ANGLES, True],
    ],
)
def test_answer_type_allows_null(answer_type, allow_null):
    q = Question(answer_type=answer_type)
    assert q.is_answer_valid(answer=None) == allow_null
