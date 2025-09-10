import re
from pathlib import Path

import pytest
from django.urls import reverse

from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.components.models import InterfaceKind
from grandchallenge.core.utils.query import set_seed
from grandchallenge.reader_studies.models import (
    Answer,
    AnswerType,
    DisplaySet,
    Question,
    QuestionWidgetKindChoices,
)
from grandchallenge.reader_studies.views import DisplaySetViewSet
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    CategoricalOptionFactory,
    DisplaySetFactory,
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.reader_studies_tests.utils import TwoReaderStudies
from tests.uploads_tests.factories import (
    create_completed_upload,
    create_upload_from_file,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_api_list_is_filtered(client):
    rs1, rs2 = ReaderStudyFactory(), ReaderStudyFactory()
    rs1_editor = UserFactory()
    rs1.add_editor(rs1_editor)
    q1, q2 = (
        QuestionFactory(reader_study=rs1),
        QuestionFactory(reader_study=rs2),
    )
    a1, _ = (
        AnswerFactory(question=q1, answer=True),
        AnswerFactory(question=q2, answer=False),
    )

    response = get_view_for_user(
        viewname="api:reader-study-list", user=rs1_editor, client=client
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1

    response = get_view_for_user(
        viewname="api:reader-study-detail",
        reverse_kwargs={"pk": rs1.pk},
        user=rs1_editor,
        client=client,
    )
    assert response.status_code == 200
    assert len(response.json()["questions"]) == 1

    response = get_view_for_user(
        viewname="api:reader-studies-question-list",
        user=rs1_editor,
        client=client,
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["pk"] == str(q1.pk)

    response = get_view_for_user(
        viewname="api:reader-studies-answer-list",
        user=rs1_editor,
        client=client,
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["pk"] == str(a1.pk)


@pytest.mark.django_db
def test_answer_create(client):
    im = ImageFactory()
    civ = ComponentInterfaceValueFactory(image=im)
    rs = ReaderStudyFactory()

    ds = DisplaySetFactory(reader_study=rs)
    ds.values.add(civ)

    rs.display_sets.add()
    rs.save()

    reader = UserFactory()
    rs.add_reader(reader)

    q = QuestionFactory(reader_study=rs, answer_type=Question.AnswerType.BOOL)

    response = get_view_for_user(
        viewname="api:reader-studies-answer-list",
        user=reader,
        client=client,
        method=client.post,
        data={
            "answer": True,
            "display_set": ds.api_url,
            "question": q.api_url,
        },
        content_type="application/json",
    )
    assert response.status_code == 201

    answer = Answer.objects.get(pk=response.data.get("pk"))

    assert answer.creator == reader
    assert answer.display_set == ds
    assert answer.question == q
    assert answer.answer is True


@pytest.mark.django_db
def test_answer_update(client):
    im = ImageFactory()
    civ = ComponentInterfaceValueFactory(image=im)
    rs = ReaderStudyFactory()

    ds = DisplaySetFactory(reader_study=rs)
    ds.values.add(civ)

    rs.display_sets.add()
    rs.save()

    reader = UserFactory()
    rs.add_reader(reader)

    editor = UserFactory()
    rs.add_editor(editor)

    q = QuestionFactory(reader_study=rs, answer_type=Question.AnswerType.BOOL)

    response = get_view_for_user(
        viewname="api:reader-studies-answer-list",
        user=reader,
        client=client,
        method=client.post,
        data={
            "answer": True,
            "display_set": ds.api_url,
            "question": q.api_url,
        },
        content_type="application/json",
    )
    assert response.status_code == 201

    answer = Answer.objects.get(pk=response.data.get("pk"))
    assert answer.answer is True
    assert answer.display_set == ds

    response = get_view_for_user(
        viewname="api:reader-studies-answer-detail",
        reverse_kwargs={"pk": answer.pk},
        user=reader,
        client=client,
        method=client.patch,
        data={"answer": False, "display_set": ds.api_url},
        content_type="application/json",
    )
    assert response.status_code == 400

    answer.refresh_from_db()
    assert response.json() == {
        "non_field_errors": [
            "This reader study does not allow answer modification."
        ]
    }
    assert answer.answer is True
    assert answer.display_set == ds

    rs.allow_answer_modification = True
    rs.save()

    response = get_view_for_user(
        viewname="api:reader-studies-answer-detail",
        reverse_kwargs={"pk": answer.pk},
        user=reader,
        client=client,
        method=client.patch,
        data={"answer": False, "display_set": ds.api_url},
        content_type="application/json",
    )
    assert response.status_code == 400

    answer.refresh_from_db()
    assert response.json() == {
        "non_field_errors": [
            "Only the answer and last_edit_duration field can be modified."
        ]
    }
    assert answer.answer is True
    assert answer.display_set == ds

    response = get_view_for_user(
        viewname="api:reader-studies-answer-detail",
        reverse_kwargs={"pk": answer.pk},
        user=reader,
        client=client,
        method=client.patch,
        data={"answer": False},
        content_type="application/json",
    )
    assert response.status_code == 200

    answer.refresh_from_db()
    assert answer.answer is False
    assert answer.display_set == ds

    response = get_view_for_user(
        viewname="api:reader-studies-answer-detail",
        reverse_kwargs={"pk": answer.pk},
        user=editor,
        client=client,
        method=client.patch,
        data={"answer": False},
        content_type="application/json",
    )
    assert response.status_code == 403

    answer.refresh_from_db()
    assert answer.answer is False


@pytest.mark.django_db
def test_answer_creator_is_reader(client):
    rs_set = TwoReaderStudies()
    ds = DisplaySetFactory(reader_study=rs_set.rs1)

    q = QuestionFactory(
        reader_study=rs_set.rs1, answer_type=Question.AnswerType.BOOL
    )

    tests = (
        (rs_set.editor1, 201),
        (rs_set.reader1, 201),
        (rs_set.editor2, 400),
        (rs_set.reader2, 400),
        (rs_set.u, 400),
    )

    for test in tests:
        response = get_view_for_user(
            viewname="api:reader-studies-answer-list",
            user=test[0],
            client=client,
            method=client.post,
            data={
                "answer": True,
                "display_set": ds.api_url,
                "question": q.api_url,
            },
            content_type="application/json",
        )
        assert response.status_code == test[1]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "answer_type,answer,expected",
    (
        (Question.AnswerType.BOOL, True, 201),
        (Question.AnswerType.BOOL, "True", 400),
        (Question.AnswerType.BOOL, 12, 400),
        (Question.AnswerType.NUMBER, 12, 201),
        (Question.AnswerType.NUMBER, "12", 400),
        (Question.AnswerType.NUMBER, True, 400),
        (Question.AnswerType.TEXT, "dgfsgfds", 201),
        (Question.AnswerType.TEXT, None, 400),
        (Question.AnswerType.TEXT, True, 400),
        (Question.AnswerType.TEXT, 12, 400),
        (Question.AnswerType.MULTIPLE_CHOICE, None, 400),
        # Headings are always incorrect when answering
        (Question.AnswerType.HEADING, True, 400),
        (Question.AnswerType.HEADING, "null", 400),
        # Annotations
        (Question.AnswerType.BOUNDING_BOX_2D, "", 400),
        (Question.AnswerType.BOUNDING_BOX_2D, True, 400),
        (Question.AnswerType.BOUNDING_BOX_2D, False, 400),
        (Question.AnswerType.BOUNDING_BOX_2D, 134, 400),
        (Question.AnswerType.BOUNDING_BOX_2D, "dsfuag", 400),
        (Question.AnswerType.BOUNDING_BOX_2D, {}, 400),
        (
            Question.AnswerType.BOUNDING_BOX_2D,
            {
                "version": {"major": 1, "minor": 0},
                "type": "2D bounding box",
                "name": "test_name",
                "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 0, 0]],
            },
            201,
        ),
        (
            Question.AnswerType.BOUNDING_BOX_2D,
            {
                "type": "2D bounding box",
                "name": "test_name",
                "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 0, 0]],
            },
            400,
        ),
        (
            Question.AnswerType.BOUNDING_BOX_2D,
            {
                "version": {"major": 1, "minor": 0},
                "name": "test_name",
                "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 0, 0]],
            },
            400,
        ),
        (
            Question.AnswerType.BOUNDING_BOX_2D,
            '{"version": {"major": 1, "minor": 0}, "type": "2D bounding box", "name": "test_name", "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 0, 0]]}',
            400,
        ),  # Valid json, but a string
        (Question.AnswerType.MULTIPLE_2D_BOUNDING_BOXES, "", 400),
        (Question.AnswerType.MULTIPLE_2D_BOUNDING_BOXES, True, 400),
        (Question.AnswerType.MULTIPLE_2D_BOUNDING_BOXES, False, 400),
        (Question.AnswerType.MULTIPLE_2D_BOUNDING_BOXES, 134, 400),
        (Question.AnswerType.MULTIPLE_2D_BOUNDING_BOXES, "dsfuag", 400),
        (Question.AnswerType.MULTIPLE_2D_BOUNDING_BOXES, {}, 400),
        (
            Question.AnswerType.MULTIPLE_2D_BOUNDING_BOXES,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple 2D bounding boxes",
                "name": "test_name",
                "boxes": [
                    {
                        "corners": [
                            [0, 0, 0],
                            [10, 0, 0],
                            [10, 10, 0],
                            [0, 0, 0],
                        ]
                    }
                ],
            },
            201,
        ),
        (
            Question.AnswerType.MULTIPLE_2D_BOUNDING_BOXES,
            {
                "type": "2D bounding box",
                "name": "test_name",
                "boxes": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 0, 0]],
            },
            400,
        ),
        (
            Question.AnswerType.MULTIPLE_2D_BOUNDING_BOXES,
            {
                "version": {"major": 1, "minor": 0},
                "name": "test_name",
                "boxes": [
                    {
                        "corners": [
                            [0, 0, 0],
                            [10, 0, 0],
                            [10, 10, 0],
                            [0, 0, 0],
                        ]
                    }
                ],
            },
            400,
        ),
        (
            Question.AnswerType.MULTIPLE_2D_BOUNDING_BOXES,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple 2D bounding boxes",
                "name": "test_name",
                "boxes": [
                    {
                        "corners": [
                            [0, 0, 0],
                            [10, 0, 0],
                            [10, 10, 0],
                            [0, 0, 0],
                        ]
                    },
                    {
                        "corners": [
                            [0, 0, 0],
                            [10, 0, 0],
                            [10, 10, 0],
                            [0, 0, 0],
                        ]
                    },
                ],
            },
            201,
        ),
        (
            Question.AnswerType.DISTANCE_MEASUREMENT,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Distance measurement",
                "name": "test",
                "start": (1, 2, 3),
                "end": (4, 5, 6),
            },
            201,
        ),
        (
            Question.AnswerType.DISTANCE_MEASUREMENT,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Distance measurement",
                "name": "test",
                "end": (4, 5, 6),
            },
            400,
        ),
        (
            Question.AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple distance measurements",
                "lines": [{"start": (1, 2, 3), "end": (4, 5, 6)}],
            },
            201,
        ),
        (
            Question.AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple distance measurements",
                "name": "test",
                "lines": [
                    {"start": (1, 2, 3), "end": (4, 5, 6)},
                    {"start": (1, 2, 3), "end": (4, 5, 6)},
                ],
            },
            201,
        ),
        (
            Question.AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple distance measurements",
                "name": "test",
                "lines": [{"start": (1, 2, 3), "end": (4, 5, 6)}],
            },
            201,
        ),
        (
            Question.AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Distance measurements",
                "name": "test",
                "lines": [{"start": (1, 2, 3), "end": (4, 5, 6)}],
            },
            400,
        ),
        (
            Question.AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple distance measurements",
                "name": "test",
                "lines": [{"start": (1, 2, 3)}],
            },
            400,
        ),
        (
            Question.AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple distance measurements",
                "name": "test",
                "lines": [
                    {"start": (1, 2, 3)},
                    {"start": (1, 2, 3), "end": (4, 5, 6)},
                ],
            },
            400,
        ),
        (
            Question.AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS,
            {
                "type": "Multiple distance measurements",
                "lines": [{"start": (1, 2, 3), "end": (4, 5, 6)}],
            },
            400,
        ),
        (
            Question.AnswerType.POINT,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Point",
                "name": "test",
                "point": (1, 2, 3),
            },
            201,
        ),
        (
            Question.AnswerType.POINT,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Point",
                "name": "test",
                "point": (1, 2),
            },
            400,
        ),
        (
            Question.AnswerType.MULTIPLE_POINTS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple points",
                "name": "test",
                "points": [{"point": (1, 2, 3)}, {"point": (4, 5, 6)}],
            },
            201,
        ),
        (
            Question.AnswerType.MULTIPLE_POINTS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple points",
                "name": "test",
                "points": [{"point": (1, 2)}, {"point": (4, 5, 6)}],
            },
            400,
        ),
        (
            Question.AnswerType.POLYGON,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Polygon",
                "name": "test",
                "seed_point": (1, 2, 3),
                "path_points": [(1, 2, 3), (4, 5, 6)],
                "sub_type": "poly",
                "groups": ["a", "b"],
            },
            201,
        ),
        (
            Question.AnswerType.POLYGON,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Polygon",
                "name": "test",
                "path_points": [(1, 2, 3), (4, 5, 6)],
                "sub_type": "poly",
                "groups": ["a", "b"],
            },
            400,
        ),
        (
            Question.AnswerType.POLYGON,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Polygon",
                "name": "test",
                "seed_point": (1, 2, 3),
                "sub_type": "poly",
                "groups": ["a", "b"],
            },
            400,
        ),
        (
            Question.AnswerType.POLYGON,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Polygon",
                "name": "test",
                "seed_point": (1, 2, 3),
                "path_points": [(1, 2, 3), (4, 5, 6)],
                "sub_type": "poly",
            },
            400,
        ),
        (
            Question.AnswerType.POLYGON,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Polygon",
                "name": "test",
                "seed_point": (1, 2, 3),
                "path_points": [(1, 2, 3), (4, 5, 6)],
                "groups": ["a", "b"],
            },
            400,
        ),
        (
            Question.AnswerType.MULTIPLE_POLYGONS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple polygons",
                "name": "test",
                "polygons": [
                    {
                        "name": "test",
                        "seed_point": (1, 2, 3),
                        "path_points": [(1, 2, 3), (4, 5, 6)],
                        "sub_type": "poly",
                        "groups": ["a", "b"],
                    }
                ],
            },
            201,
        ),
        (
            Question.AnswerType.MULTIPLE_POLYGONS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple polygons",
                "name": "test",
                "polygons": [
                    {
                        "seed_point": (1, 2, 3),
                        "path_points": [(1, 2, 3), (4, 5, 6)],
                        "sub_type": "poly",
                        "groups": ["a", "b"],
                    }
                ],
            },
            201,
        ),
        (
            Question.AnswerType.ANGLE,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Angle",
                "name": "test",
                "lines": (((1, 2, 3), (4, 5, 6)), ((7, 8, 9), (10, 11, 12))),
            },
            201,
        ),
        (
            Question.AnswerType.ANGLE,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Angle",
                "name": "test",
                "lines": (
                    ((1, 2, 3), (4, 5, 6), (7, 8, 9)),
                    ((7, 8, 9), (10, 11, 12)),
                ),
            },
            400,
        ),
        (
            Question.AnswerType.ANGLE,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Angle",
                "name": "test",
                "lines": (((1, 2, 3), (4, 5, 6)),),
            },
            400,
        ),
        (
            Question.AnswerType.ANGLE,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Angle",
                "name": "test",
                "lines": (
                    ((1, 2, 3), (4, 5, 6, 7)),
                    ((7, 8, 9), (10, 11, 12)),
                ),
            },
            400,
        ),
        (
            Question.AnswerType.MULTIPLE_ANGLES,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple angles",
                "name": "test",
                "angles": [
                    {
                        "lines": (
                            ((1, 2, 3), (4, 5, 6)),
                            ((7, 8, 9), (10, 11, 12)),
                        ),
                    },
                    {
                        "lines": (
                            ((1, 2, 3), (4, 5, 6)),
                            ((7, 8, 9), (10, 11, 12)),
                        )
                    },
                ],
            },
            201,
        ),
        (
            Question.AnswerType.MULTIPLE_ANGLES,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple angles",
                "name": "test",
                "angles": [],
            },
            201,
        ),
        (
            Question.AnswerType.MULTIPLE_ANGLES,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple angles",
                "name": "test",
                "angles": [
                    {
                        "lines": (
                            ((1, 2, 3), (4, 5, 6)),
                            ((7, 8, 9), (10, 11, 12), (13, 14, 15)),
                        ),
                    },
                    {
                        "lines": (
                            ((1, 2, 3), (4, 5, 6)),
                            ((7, 8, 9), (10, 11, 12)),
                        )
                    },
                ],
            },
            400,
        ),
        (
            Question.AnswerType.MULTIPLE_ANGLES,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple angles",
                "name": "test",
                "angles": [
                    {
                        "lines": (((1, 2, 3), (4, 5, 6)),),
                    },
                    {
                        "lines": (
                            ((1, 2, 3), (4, 5, 6)),
                            ((7, 8, 9), (10, 11, 12)),
                        )
                    },
                ],
            },
            400,
        ),
        (
            Question.AnswerType.MULTIPLE_ANGLES,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple angles",
                "name": "test",
                "angles": [
                    {
                        "lines": (
                            ((1, 2, 3, 4), (4, 5, 6)),
                            ((7, 8, 9), (10, 11, 12)),
                        ),
                    },
                    {
                        "lines": (
                            ((1, 2, 3), (4, 5, 6)),
                            ((7, 8, 9), (10, 11, 12)),
                        )
                    },
                ],
            },
            400,
        ),
        (Question.AnswerType.ELLIPSE, "wwoljg", 400),
        (Question.AnswerType.ELLIPSE, True, 400),
        (Question.AnswerType.ELLIPSE, 42, 400),
        (Question.AnswerType.ELLIPSE, {}, 400),
        (Question.AnswerType.ELLIPSE, "", 400),
        (
            Question.AnswerType.ELLIPSE,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Ellipse",
                "name": "test",
                "major_axis": ((1, 2, 3), (4, 5, 6)),
                "minor_axis": ((7, 8, 9), (10, 11, 12)),
            },
            201,
        ),
        (
            Question.AnswerType.ELLIPSE,
            {
                "version": {"major": 1, "minor": 0},
                "type": "ELLIPSE",
                "name": "test",
                "major_axis": ((1, 2, 3), (4, 5, 6), (7, 8, 9)),
                "minor_axis": ((7, 8, 9), (10, 11, 12)),
            },
            400,
        ),
        (
            Question.AnswerType.ELLIPSE,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Ellipse",
                "name": "test",
                "major_axis": (((1, 2, 3), (4, 5, 6)),),
                "minor_axis": ((1, 2, 3), (4, 5, 6)),
            },
            400,
        ),
        (
            Question.AnswerType.ELLIPSE,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Ellipse",
                "name": "test",
                "major_axis": ((1, 2, 3), (4, 5, 6, 7)),
                "minor_axis": ((7, 8, 9), (10, 11, 12)),
            },
            400,
        ),
        (Question.AnswerType.MULTIPLE_ELLIPSES, "djwqpidg", 400),
        (Question.AnswerType.MULTIPLE_ELLIPSES, True, 400),
        (Question.AnswerType.MULTIPLE_ELLIPSES, 42, 400),
        (Question.AnswerType.MULTIPLE_ELLIPSES, {}, 400),
        (Question.AnswerType.MULTIPLE_ELLIPSES, "", 400),
        (
            Question.AnswerType.MULTIPLE_ELLIPSES,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple ellipses",
                "name": "test",
                "ellipses": [
                    {
                        "name": "ellipse1",
                        "major_axis": ((1, 2, 3), (4, 5, 6)),
                        "minor_axis": ((7, 8, 9), (10, 11, 12)),
                    }
                ],
            },
            201,
        ),
        (
            Question.AnswerType.MULTIPLE_ELLIPSES,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple ellipses",
                "name": "test",
                "ellipses": [
                    {
                        "name": "ellipse1",
                        "major_axis": ((1, 2, 3), (4, 5, 6), (4, 5, 6)),
                        "minor_axis": ((7, 8, 9), (10, 11, 12)),
                    }
                ],
            },
            400,
        ),
        (
            Question.AnswerType.MULTIPLE_ELLIPSES,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple ellipses",
                "name": "test",
                "ellipses": [
                    {
                        "name": "ellipse1",
                        "major_axis": ((1, 2, 3), (4, 5, 6)),
                        "minor_axis": ((7, 8, 9), (10, 11, 12)),
                    },
                    {
                        "name": "ellipse2",
                        "major_axis": ((1, 2, 3)),
                        "minor_axis": ((7, 8, 9), (10, 11, 12)),
                    },
                ],
            },
            400,
        ),
    ),
)
def test_answer_is_correct_type(client, answer_type, answer, expected):
    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)

    reader = UserFactory()
    rs.add_reader(reader)

    q = QuestionFactory(reader_study=rs, answer_type=answer_type)

    response = get_view_for_user(
        viewname="api:reader-studies-answer-list",
        user=reader,
        client=client,
        method=client.post,
        data={
            "answer": answer,
            "display_set": ds.api_url,
            "question": q.api_url,
        },
        content_type="application/json",
    )
    assert response.status_code == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "answer_type,answer",
    (
        # Blank answers
        (Question.AnswerType.TEXT, ""),
        # Null answers
        (Question.AnswerType.NUMBER, None),
        (Question.AnswerType.CHOICE, None),
        (Question.AnswerType.BOUNDING_BOX_2D, None),
        (Question.AnswerType.MULTIPLE_2D_BOUNDING_BOXES, None),
        (Question.AnswerType.DISTANCE_MEASUREMENT, None),
        (Question.AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS, None),
        (Question.AnswerType.POINT, None),
        (Question.AnswerType.MULTIPLE_POINTS, None),
        (Question.AnswerType.POLYGON, None),
        (Question.AnswerType.MULTIPLE_POLYGONS, None),
        (Question.AnswerType.LINE, None),
        (Question.AnswerType.MULTIPLE_LINES, None),
        (Question.AnswerType.ANGLE, None),
        (Question.AnswerType.MULTIPLE_ANGLES, None),
        (Question.AnswerType.ELLIPSE, None),
        (Question.AnswerType.MULTIPLE_ELLIPSES, None),
        # Empty-collection answers
        (Question.AnswerType.MULTIPLE_CHOICE, []),
    ),
)
@pytest.mark.parametrize(
    "is_required,expected_status_code",
    (
        (False, 201),
        (True, 400),
    ),
)
def test_empty_answers(
    client, answer_type, answer, is_required, expected_status_code
):
    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)
    reader = UserFactory()
    rs.add_reader(reader)

    q = QuestionFactory(
        reader_study=rs,
        answer_type=answer_type,
        required=is_required,
    )

    response = get_view_for_user(
        viewname="api:reader-studies-answer-list",
        user=reader,
        client=client,
        method=client.post,
        data={
            "answer": answer,
            "display_set": ds.api_url,
            "question": q.api_url,
        },
        content_type="application/json",
    )
    assert response.status_code == expected_status_code


@pytest.mark.django_db
def test_mine(client):
    rs1, rs2 = ReaderStudyFactory(), ReaderStudyFactory()
    ds1 = DisplaySetFactory(reader_study=rs1)
    ds2 = DisplaySetFactory(reader_study=rs2)

    reader = UserFactory()
    rs1.add_reader(reader)
    rs2.add_reader(reader)

    q1 = QuestionFactory(
        reader_study=rs1, answer_type=Question.AnswerType.BOOL
    )
    q2 = QuestionFactory(
        reader_study=rs2, answer_type=Question.AnswerType.BOOL
    )

    a1 = AnswerFactory(
        question=q1, creator=reader, answer=True, display_set=ds1
    )

    a2 = AnswerFactory(
        question=q2, creator=reader, answer=True, display_set=ds2
    )

    response = get_view_for_user(
        viewname="api:reader-studies-answer-mine",
        user=reader,
        client=client,
        method=client.get,
        content_type="application/json",
    )
    response = response.json()
    assert response["count"] == 2

    response = get_view_for_user(
        viewname="api:reader-studies-answer-mine",
        user=reader,
        client=client,
        method=client.get,
        data={"question__reader_study": rs1.pk},
        content_type="application/json",
    )
    response = response.json()
    assert response["count"] == 1
    assert response["results"][0]["pk"] == str(a1.pk)

    response = get_view_for_user(
        viewname="api:reader-studies-answer-mine",
        user=reader,
        client=client,
        method=client.get,
        data={"question__reader_study": rs2.pk},
        content_type="application/json",
    )
    response = response.json()
    assert response["count"] == 1
    assert response["results"][0]["pk"] == str(a2.pk)


@pytest.mark.django_db
def test_ground_truth_is_excluded(client):
    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)
    editor = UserFactory()
    rs.add_editor(editor)
    rs.add_reader(editor)

    q = QuestionFactory(reader_study=rs, answer_type=Question.AnswerType.BOOL)

    AnswerFactory(
        question=q,
        creator=editor,
        answer=True,
        is_ground_truth=True,
        display_set=ds,
    )

    a2 = AnswerFactory(
        question=q,
        creator=editor,
        answer=True,
        is_ground_truth=False,
        display_set=ds,
    )

    response = get_view_for_user(
        viewname="api:reader-studies-answer-mine",
        user=editor,
        client=client,
        method=client.get,
        content_type="application/json",
    )
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["pk"] == str(a2.pk)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "answer_type,answer",
    (
        (Question.AnswerType.BOOL, True),
        (Question.AnswerType.NUMBER, 12),
        (Question.AnswerType.TEXT, "dgfsgfds"),
        (
            Question.AnswerType.BOUNDING_BOX_2D,
            {
                "version": {"major": 1, "minor": 0},
                "type": "2D bounding box",
                "name": "test_name",
                "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 0, 0]],
            },
        ),
        (
            Question.AnswerType.DISTANCE_MEASUREMENT,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Distance measurement",
                "name": "test",
                "start": (1, 2, 3),
                "end": (4, 5, 6),
            },
        ),
        (
            Question.AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple distance measurements",
                "name": "test",
                "lines": [
                    {"start": (1, 2, 3), "end": (4, 5, 6)},
                    {"start": (1, 2, 3), "end": (4, 5, 6)},
                ],
            },
        ),
    ),
)
def test_csv_export(client, answer_type, answer):
    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)

    editor = UserFactory()
    rs.add_editor(editor)

    reader = UserFactory()
    rs.add_reader(reader)

    q = QuestionFactory(
        question_text="foo", reader_study=rs, answer_type=answer_type
    )

    a = AnswerFactory(question=q, answer=answer, display_set=ds)

    response = get_view_for_user(
        viewname="api:reader-studies-answer-list",
        params={"question__reader_study": str(rs.pk)},
        user=editor,
        client=client,
        method=client.get,
        HTTP_ACCEPT="text/csv",
    )

    headers = str(response.serialize_headers())
    content = str(response.content)
    assert response.status_code == 200
    assert "Content-Type: text/csv" in headers

    if isinstance(answer, dict):
        for key in answer:
            assert key in content
    else:
        assert re.sub(r"\n", r"\\n", str(a.answer)) in content
    assert a.creator.username in content

    response = get_view_for_user(
        viewname="api:reader-studies-question-list",
        params={"reader_study": str(rs.pk)},
        user=editor,
        client=client,
        method=client.get,
        HTTP_ACCEPT="text/csv",
    )

    headers = str(response.serialize_headers())
    content = str(response.content)

    assert response.status_code == 200
    assert "Content-Type: text/csv" in headers

    assert a.question.question_text in content
    assert a.question.get_answer_type_display() in content
    assert str(a.question.required) in content
    assert a.question.get_image_port_display() in content

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        params={"reader_study": str(rs.pk)},
        user=editor,
        client=client,
        method=client.get,
        HTTP_ACCEPT="text/csv",
    )

    headers = str(response.serialize_headers())
    content = str(response.content)

    assert response.status_code == 200
    assert "Content-Type: text/csv" in headers

    assert str(ds.pk) in content


@pytest.mark.django_db
def test_ground_truth(client):
    rs = ReaderStudyFactory(
        is_educational=True,
    )
    reader = UserFactory()
    rs.add_reader(reader)

    q1 = QuestionFactory(
        answer_type=Question.AnswerType.CHOICE, reader_study=rs
    )
    q2 = QuestionFactory(
        answer_type=Question.AnswerType.MULTIPLE_CHOICE, reader_study=rs
    )
    q3 = QuestionFactory(
        answer_type=Question.AnswerType.MULTIPLE_CHOICE,
        widget=QuestionWidgetKindChoices.SELECT_MULTIPLE,
        reader_study=rs,
    )

    op1 = CategoricalOptionFactory(question=q1, title="option1")
    op2 = CategoricalOptionFactory(question=q2, title="option1")
    op3 = CategoricalOptionFactory(question=q2, title="option1")
    op4 = CategoricalOptionFactory(question=q3, title="option1")
    op5 = CategoricalOptionFactory(question=q3, title="option1")

    ds = DisplaySetFactory(reader_study=rs)

    AnswerFactory(
        question=q1, answer=op1.pk, is_ground_truth=True, display_set=ds
    )

    AnswerFactory(
        question=q2,
        answer=[op2.pk, op3.pk],
        is_ground_truth=True,
        display_set=ds,
    )
    AnswerFactory(
        question=q3,
        answer=[op4.pk, op5.pk],
        is_ground_truth=True,
        display_set=ds,
    )

    response = get_view_for_user(
        viewname="api:reader-study-ground-truth",
        reverse_kwargs={"pk": rs.pk, "case_pk": ds.pk},
        user=reader,
        client=client,
        content_type="application/json",
        follow=True,
    )

    assert response.status_code == 200
    response = response.json()
    assert response[str(q1.pk)] == {
        "answer": op1.pk,
        "answer_text": op1.title,
        "question_text": q1.question_text,
        "options": {str(op1.pk): op1.title},
        "explanation": "",
    }
    assert response[str(q2.pk)] == {
        "answer": [op2.pk, op3.pk],
        "answer_text": f"{op2.title}, {op3.title}",
        "question_text": q2.question_text,
        "options": {str(op2.pk): op2.title, str(op3.pk): op3.title},
        "explanation": "",
    }
    assert response[str(q3.pk)] == {
        "answer": [op4.pk, op5.pk],
        "answer_text": f"{op4.title}, {op5.title}",
        "question_text": q3.question_text,
        "options": {str(op4.pk): op4.title, str(op5.pk): op5.title},
        "explanation": "",
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "overlay_segments,error",
    (
        ([], None),
        (
            [{"name": "s1", "visible": True, "voxel_value": 0}],
            (
                "The valid voxel values for this segmentation are: {0}. "
                "This segmentation is invalid as it contains the voxel values: {1}."
            ),
        ),
        (
            [
                {"name": "s1", "visible": True, "voxel_value": 0},
                {"name": "s2", "visible": True, "voxel_value": 1},
            ],
            None,
        ),
    ),
)
def test_assign_answer_image(
    client,
    settings,
    overlay_segments,
    error,
    django_capture_on_commit_callbacks,
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    rs = ReaderStudyFactory()
    ds = DisplaySetFactory(reader_study=rs)
    editor, reader = UserFactory(), UserFactory()

    rs.add_editor(editor)
    rs.add_reader(reader)

    question = QuestionFactory(
        reader_study=rs, answer_type="MASK", overlay_segments=overlay_segments
    )

    # First post/patch the answer (ReaderStudyAnswersAPI in gcapi)
    response = get_view_for_user(
        viewname="api:reader-studies-answer-list",
        user=reader,
        client=client,
        method=client.post,
        data={
            "answer": None,  # Answer must be None to image assignment
            "display_set": ds.api_url,
            "question": question.api_url,
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    answer = Answer.objects.get(pk=response.json()["pk"])

    # Next upload the image to the answer (upload_cases in gcapi)
    upload = create_upload_from_file(
        file_path=Path(__file__).parent.parent
        / "cases_tests"
        / "resources"
        / "mask.mha",
        creator=reader,
    )
    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:upload-session-list",
            user=reader,
            client=client,
            method=client.post,
            data={"answer": str(answer.pk), "uploads": [upload.api_url]},
            content_type="application/json",
        )
    assert response.status_code == 201

    # Validate
    answer.refresh_from_db()
    us = RawImageUploadSession.objects.get(pk=response.json()["pk"])
    image = us.image_set.first()
    assert us.error_message == error
    assert (answer.answer_image == image) is not error
    assert reader.has_perm("view_image", image) is not error
    assert editor.has_perm("view_image", image) is not error


@pytest.mark.django_db
@pytest.mark.parametrize("answer_type", ("MASK",))
def test_upload_session_owned_by_answer_creator(client, settings, answer_type):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = ReaderStudyFactory()
    editor, reader = UserFactory(), UserFactory()

    rs.add_editor(editor)
    rs.add_reader(reader)

    question = QuestionFactory(reader_study=rs, answer_type=answer_type)

    answer1 = AnswerFactory(creator=reader, question=question, answer=None)

    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=editor,
        client=client,
        method=client.post,
        data={
            "answer": str(answer1.pk),
            "uploads": [create_completed_upload(user=editor).api_url],
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "object does not exist" in response.json()["answer"][0]


@pytest.mark.django_db
def test_question_accepts_image_type_answers(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = ReaderStudyFactory()
    reader = UserFactory()

    rs.add_reader(reader)

    question = QuestionFactory(
        reader_study=rs, answer_type=Question.AnswerType.BOOL
    )

    answer = AnswerFactory(creator=reader, question=question, answer=None)

    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=reader,
        client=client,
        method=client.post,
        data={
            "answer": str(answer.pk),
            "uploads": [create_completed_upload(user=reader).api_url],
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert (
        b"This question does not accept image type answers"
        in response.rendered_content
    )


@pytest.mark.django_db
def test_display_set_extended_schema(client):
    """Ensure that the added params are still included if we ever upgrade drf_spectacular."""
    response = get_view_for_user(
        viewname="api:schema",
        client=client,
        data={"format": "json"},
    )
    params = response.json()["paths"][
        reverse("api:reader-studies-display-set-list")
    ]["get"]["parameters"]
    param_names = [param["name"] for param in params]
    assert "unanswered_by_user" in param_names
    assert "user" in param_names


@pytest.mark.django_db
def test_display_set_list_filters(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    r1 = UserFactory()
    r2 = UserFactory()

    rs1, rs2 = (ReaderStudyFactory() for _ in range(2))
    rs1.add_reader(r1)
    rs1.add_reader(r2)

    rs2.add_reader(r1)
    q1, q2 = (
        QuestionFactory(reader_study=rs1, answer_type=Question.AnswerType.BOOL)
        for _ in range(2)
    )
    civ1, civ2 = (
        ComponentInterfaceValueFactory(image=ImageFactory()) for _ in range(2)
    )
    ds1, ds2 = (DisplaySetFactory(reader_study=rs1) for _ in range(2))
    ds1.values.add(civ1)
    ds2.values.add(civ2)

    civ3, civ4 = (
        ComponentInterfaceValueFactory(image=ImageFactory()) for _ in range(2)
    )
    ds3, ds4 = (DisplaySetFactory(reader_study=rs2) for _ in range(2))
    ds3.values.add(civ3)
    ds4.values.add(civ4)

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        user=r1,
        client=client,
        method=client.get,
    )

    assert response.json()["count"] == 4

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={"reader_study": str(rs1.pk)},
        user=r1,
        client=client,
        method=client.get,
    )

    assert response.json()["count"] == 2
    rs1.shuffle_hanging_list = True
    rs1.save()

    # specifying a user is only possible in combination with a reader study
    unanswered_view_query = {
        "unanswered_by_user": True,
        "user": r1.username,
    }
    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data=unanswered_view_query,
        user=r1,
        client=client,
        method=client.get,
    )

    assert response.status_code == 400
    assert response.json() == [
        "Please provide a reader study when filtering for unanswered display_sets."
    ]
    unanswered_view_query["reader_study"] = str(rs1.pk)

    # specifying a user is only possible in combination with unanswered_by_user=True
    unanswered_view_query.pop("user")
    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={
            "reader_study": str(rs1.pk),
            "user": r1.username,
        },
        user=r1,
        client=client,
        method=client.get,
    )
    assert response.status_code == 400
    assert (
        "Specifying a user is only possible when retrieving unanswered display sets."
        in str(response.rendered_content)
    )

    unanswered_view_query["user"] = r1.username

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data=unanswered_view_query,
        user=r1,
        client=client,
        method=client.get,
    )

    assert response.json()["count"] == 2

    # Adding ground truths does not change anything
    AnswerFactory(
        question=q1, display_set=ds1, creator=r1, is_ground_truth=True
    )
    AnswerFactory(
        question=q2, display_set=ds1, creator=r1, is_ground_truth=True
    )

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data=unanswered_view_query,
        user=r1,
        client=client,
        method=client.get,
    )

    assert response.json()["count"] == 2

    # Partial answered cases are counted
    AnswerFactory(question=q1, display_set=ds1, creator=r1)
    AnswerFactory(
        question=q1, display_set=ds1, creator=r2
    )  # Add confounding answers for display set ds1

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data=unanswered_view_query,
        user=r1,
        client=client,
        method=client.get,
    )

    assert response.json()["count"] == 2

    AnswerFactory(question=q2, display_set=ds1, creator=r1)

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data=unanswered_view_query,
        user=r1,
        client=client,
        method=client.get,
    )

    assert response.json()["count"] == 1


@pytest.mark.django_db
def test_display_set_shuffling(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    r1, r2 = UserFactory(), UserFactory()

    rs = ReaderStudyFactory()
    rs.add_reader(r1)
    rs.add_reader(r2)

    for _ in range(20):
        civ = ComponentInterfaceValueFactory(image=ImageFactory())
        ds = DisplaySetFactory(reader_study=rs)
        ds.values.add(civ)

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={"reader_study": str(rs.pk)},
        user=r1,
        client=client,
        method=client.get,
    )

    r1_unshuffled = response.json()

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={"reader_study": str(rs.pk)},
        user=r2,
        client=client,
        method=client.get,
    )

    r2_unshuffled = response.json()

    assert r1_unshuffled == r2_unshuffled

    rs.shuffle_hanging_list = True
    rs.save()

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={"reader_study": str(rs.pk)},
        user=r1,
        client=client,
        method=client.get,
    )

    r1_shuffled_1 = response.json()

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={"reader_study": str(rs.pk)},
        user=r2,
        client=client,
        method=client.get,
    )

    r2_shuffled_1 = response.json()

    assert r1_shuffled_1 != r2_shuffled_1
    assert r1_shuffled_1 != r1_unshuffled
    assert r2_shuffled_1 != r2_unshuffled

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={"reader_study": str(rs.pk)},
        user=r1,
        client=client,
        method=client.get,
    )

    r1_shuffled_2 = response.json()

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={"reader_study": str(rs.pk)},
        user=r2,
        client=client,
        method=client.get,
    )

    r2_shuffled_2 = response.json()

    assert r1_shuffled_1 == r1_shuffled_2
    assert r2_shuffled_1 == r2_shuffled_2


@pytest.mark.django_db
def test_display_set_add_and_edit(
    client, settings, django_capture_on_commit_callbacks
):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    r1, r2 = UserFactory(), UserFactory()

    rs = ReaderStudyFactory()
    rs.add_editor(r1)
    rs.add_reader(r2)

    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.BOOL
    )

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        user=r1,
        client=client,
        method=client.post,
        content_type="application/json",
        data={
            "reader_study": rs.slug,
            "values": [{"interface": ci.slug, "value": True}],
        },
    )
    assert response.json() == ["Values can only be added via update"]

    # Add display set
    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        user=r1,
        client=client,
        method=client.post,
        content_type="application/json",
        data={"reader_study": rs.slug},
    )

    assert response.status_code == 201

    ds = DisplaySet.objects.get(pk=response.json()["pk"])
    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:upload-session-list",
            user=r1,
            client=client,
            method=client.post,
            content_type="application/json",
            data={
                "display_set": ds.pk,
                "interface": "generic-medical-image",
                "uploads": [
                    create_upload_from_file(
                        file_path=Path(__file__).parent.parent
                        / "cases_tests"
                        / "resources"
                        / "test_grayscale.jpg",
                        creator=r1,
                    ).api_url
                ],
            },
        )

    ds.refresh_from_db()
    assert ds.values.count() == 1

    initial_value = ds.values.first()
    assert initial_value.interface.slug == "generic-medical-image"
    assert initial_value.image.name == "test_grayscale.jpg"

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:upload-session-list",
            user=r1,
            client=client,
            method=client.post,
            content_type="application/json",
            data={
                "display_set": ds.pk,
                "interface": "generic-medical-image",
                "uploads": [
                    create_upload_from_file(
                        file_path=Path(__file__).parent.parent
                        / "cases_tests"
                        / "resources"
                        / "test_grayscale.png",
                        creator=r1,
                    ).api_url
                ],
            },
        )

    ds.refresh_from_db()
    assert ds.values.count() == 1

    new = ds.values.first()
    assert new != initial_value
    assert new.interface.slug == "generic-medical-image"
    assert new.image.name == "test_grayscale.png"

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-detail",
        reverse_kwargs={"pk": ds.pk},
        user=r1,
        client=client,
        method=client.patch,
        content_type="application/json",
        data={"values": [{"interface": ci.slug, "value": True}]},
    )

    assert sorted(
        val["interface"] for val in response.json()["values"]
    ) == sorted([ci.slug, "generic-medical-image"])
    ds.refresh_from_db()
    assert ds.values.count() == 2

    ci_csv = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.CSV
    )
    upload = create_upload_from_file(
        file_path=Path(__file__).parent / "resources" / "ground_truth.csv",
        creator=r1,
    )

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:reader-studies-display-set-detail",
            reverse_kwargs={"pk": ds.pk},
            user=r1,
            client=client,
            method=client.patch,
            content_type="application/json",
            data={
                "values": [
                    {"interface": ci_csv.slug, "user_upload": upload.api_url}
                ]
            },
        )

    ds.refresh_from_db()
    assert ds.values.count() == 3

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:reader-studies-display-set-detail",
            reverse_kwargs={"pk": ds.pk},
            user=r1,
            client=client,
            method=client.put,
            content_type="application/json",
            data={
                "values": [{"interface": ci.slug, "value": True}],
            },
        )

    ds.refresh_from_db()
    assert ds.values.count() == 1

    # Test updating title and order (no values)
    assert ds.title == ""
    old_order = ds.order

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:reader-studies-display-set-detail",
            reverse_kwargs={"pk": ds.pk},
            user=r1,
            client=client,
            method=client.patch,
            content_type="application/json",
            data={
                "title": "foo",
                "order": old_order + 1,
            },
        )

    assert response.status_code == 200
    ds.refresh_from_db()
    assert ds.title == "foo"
    assert ds.order == old_order + 1
    assert ds.values.count() == 1

    # Create another display set
    ds2 = DisplaySetFactory(reader_study=rs)
    civ = ComponentInterfaceValueFactory(interface=ci, value=False)
    ds2.values.add(civ)

    assert ds2.values.count() == 1

    q = QuestionFactory(reader_study=rs, answer_type=Question.AnswerType.BOOL)
    AnswerFactory(question=q, creator=r2, display_set=ds)

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-detail",
        reverse_kwargs={"pk": ds.pk},
        user=r1,
        client=client,
        method=client.patch,
        content_type="application/json",
        data={"values": [{"interface": ci.slug, "value": True}]},
    )

    assert response.status_code == 400
    assert response.json() == [
        "This display set cannot be changed, as answers for it already exist."
    ]


@pytest.mark.django_db
def test_display_set_partial_update_errors_returned(client):
    ds = DisplaySetFactory()
    user = UserFactory()
    ds.reader_study.add_editor(user)
    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.STRING
    )
    response = get_view_for_user(
        viewname="api:reader-studies-display-set-detail",
        reverse_kwargs={"pk": ds.pk},
        user=user,
        client=client,
        method=client.patch,
        content_type="application/json",
        data={"values": [{"interface": ci.slug, "value": 11}]},
    )
    assert response.status_code == 400
    assert "JSON does not fulfill schema" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_display_sets_shuffled_per_user(client):
    n_display_sets = 10
    reader_study = ReaderStudyFactory(shuffle_hanging_list=False)
    user1, user2 = UserFactory.create_batch(2)

    reader_study.add_reader(user1)
    reader_study.add_reader(user2)

    DisplaySetFactory.create_batch(n_display_sets, reader_study=reader_study)

    for user in [user1, user2]:
        response = get_view_for_user(
            viewname="api:reader-studies-display-set-list",
            data={"reader_study": str(reader_study.pk)},
            user=user,
            client=client,
            method=client.get,
        )

        assert [x["index"] for x in response.json()["results"]] == [
            *range(n_display_sets)
        ]
        assert [x["order"] for x in response.json()["results"]] == [
            *range(10, 10 * (n_display_sets + 1), 10)
        ]

    reader_study.shuffle_hanging_list = True
    reader_study.save()

    response1 = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={"reader_study": str(reader_study.pk)},
        user=user1,
        client=client,
        method=client.get,
    )
    response2 = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={"reader_study": str(reader_study.pk)},
        user=user2,
        client=client,
        method=client.get,
    )

    # Different users must have the same index
    assert [x["index"] for x in response1.json()["results"]] == [
        x["index"] for x in response2.json()["results"]
    ]
    # Different users must receive a different order
    assert [x["order"] for x in response1.json()["results"]] != [
        x["order"] for x in response2.json()["results"]
    ]
    # The ordering must be consistent
    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={"reader_study": str(reader_study.pk)},
        user=user1,
        client=client,
        method=client.get,
    )
    assert [x["order"] for x in response1.json()["results"]] == [
        x["order"] for x in response.json()["results"]
    ]


@pytest.mark.flaky(reruns=3)
@pytest.mark.django_db
def test_display_set_index(client):
    n_display_sets = 10
    reader_study = ReaderStudyFactory()
    user = UserFactory()
    reader_study.add_reader(user)

    DisplaySetFactory.create_batch(n_display_sets, reader_study=reader_study)

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={"reader_study": str(reader_study.pk)},
        user=user,
        client=client,
        method=client.get,
    )

    assert [x["index"] for x in response.json()["results"]] == [
        *range(n_display_sets)
    ]
    assert [x["order"] for x in response.json()["results"]] == [
        *range(10, 10 * (n_display_sets + 1), 10)
    ]

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-detail",
        user=user,
        client=client,
        reverse_kwargs={"pk": str(DisplaySet.objects.first().pk)},
        method=client.get,
    )

    assert response.json()["index"] == 0

    reader_study.shuffle_hanging_list = True
    reader_study.save()

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={"reader_study": str(reader_study.pk)},
        user=user,
        client=client,
        method=client.get,
    )

    last = [
        x
        for x in response.json()["results"]
        if x["pk"] == str(DisplaySet.objects.last().pk)
    ][0]
    assert [x["index"] for x in response.json()["results"]] == [
        *range(n_display_sets)
    ]
    shuffled_order = [x["order"] for x in response.json()["results"]]

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-detail",
        user=user,
        client=client,
        reverse_kwargs={"pk": str(DisplaySet.objects.first().pk)},
        method=client.get,
    )

    # determine shuffled index of first Displayset
    set_seed(1 / int(user.pk))
    queryset = list(DisplaySet.objects.all().order_by("?"))
    new_index = queryset.index(DisplaySet.objects.first())

    assert response.json()["index"] == new_index

    reader_study.shuffle_hanging_list = False
    reader_study.save()

    q = QuestionFactory(reader_study=reader_study)
    AnswerFactory(
        question=q, display_set=DisplaySet.objects.last(), creator=user
    )

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={
            "reader_study": str(reader_study.pk),
            "unanswered_by_user": "True",
        },
        user=user,
        client=client,
        method=client.get,
    )

    assert [x["index"] for x in response.json()["results"]] == [
        *range(n_display_sets - 1)
    ]
    assert [x["order"] for x in response.json()["results"]] == [
        *range(10, 10 * n_display_sets, 10)
    ]

    reader_study.shuffle_hanging_list = True
    reader_study.save()

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={
            "reader_study": str(reader_study.pk),
            "unanswered_by_user": "True",
        },
        user=user,
        client=client,
        method=client.get,
    )

    assert [x["index"] for x in response.json()["results"]] == list(
        x for x in range(n_display_sets) if x is not last["index"]
    )
    assert [x["order"] for x in response.json()["results"]] == [
        x for x in shuffled_order if x != last["order"]
    ]


@pytest.mark.django_db
def test_display_set_index_with_duplicate_order(
    client, django_assert_num_queries
):
    reader_study = ReaderStudyFactory()
    user = UserFactory()
    reader_study.add_reader(user)

    ds1, ds2, *_ = DisplaySetFactory.create_batch(3, reader_study=reader_study)

    ds2.order = ds1.order
    ds2.save()

    with django_assert_num_queries(34):
        response = get_view_for_user(
            viewname="api:reader-studies-display-set-list",
            data={"reader_study": str(reader_study.pk)},
            user=user,
            client=client,
            method=client.get,
        )

    assert [x["index"] for x in response.json()["results"]] == [0, 1, 2]


@pytest.mark.django_db
def test_total_edit_duration(client):
    rs = ReaderStudyFactory(allow_answer_modification=True)
    ds = DisplaySetFactory(reader_study=rs)
    q = QuestionFactory(reader_study=rs, answer_type=AnswerType.TEXT)
    u = UserFactory()

    rs.add_reader(u)

    response = get_view_for_user(
        viewname="api:reader-studies-answer-list",
        user=u,
        client=client,
        method=client.post,
        content_type="application/json",
        data={
            "question": q.api_url,
            "display_set": ds.api_url,
            "answer": "foo",
        },
    )

    assert response.status_code == 201
    assert response.json()["last_edit_duration"] is None
    assert response.json()["total_edit_duration"] is None

    pk = response.json()["pk"]

    response = get_view_for_user(
        viewname="api:reader-studies-answer-detail",
        user=u,
        client=client,
        method=client.patch,
        reverse_kwargs={"pk": pk},
        content_type="application/json",
        data={"answer": "bar", "last_edit_duration": "00:30"},
    )
    assert response.status_code == 200
    assert response.json()["last_edit_duration"] == "00:00:30"
    assert response.json()["total_edit_duration"] is None

    Answer.objects.all().delete()

    response = get_view_for_user(
        viewname="api:reader-studies-answer-list",
        user=u,
        client=client,
        method=client.post,
        content_type="application/json",
        data={
            "question": q.api_url,
            "display_set": ds.api_url,
            "answer": "foo",
            "last_edit_duration": "00:30",
        },
    )

    assert response.status_code == 201
    assert response.json()["last_edit_duration"] == "00:00:30"
    assert response.json()["total_edit_duration"] == "00:00:30"

    pk = response.json()["pk"]

    response = get_view_for_user(
        viewname="api:reader-studies-answer-detail",
        user=u,
        client=client,
        method=client.patch,
        reverse_kwargs={"pk": pk},
        content_type="application/json",
        data={"answer": "bar", "last_edit_duration": "00:30"},
    )

    assert response.status_code == 200
    assert response.json()["last_edit_duration"] == "00:00:30"
    assert response.json()["total_edit_duration"] == "00:01:00"

    response = get_view_for_user(
        viewname="api:reader-studies-answer-detail",
        user=u,
        client=client,
        method=client.patch,
        reverse_kwargs={"pk": pk},
        content_type="application/json",
        data={"answer": "bar"},
    )

    assert response.status_code == 200
    assert response.json()["last_edit_duration"] is None
    assert response.json()["total_edit_duration"] is None

    response = get_view_for_user(
        viewname="api:reader-studies-answer-detail",
        user=u,
        client=client,
        method=client.patch,
        reverse_kwargs={"pk": pk},
        content_type="application/json",
        data={"answer": "bar", "last_edit_duration": "00:30"},
    )

    assert response.status_code == 200
    assert response.json()["last_edit_duration"] == "00:00:30"
    assert response.json()["total_edit_duration"] is None


def test_display_set_filterset_fields_is_only_reader_sudy():
    ds_viewset = DisplaySetViewSet()
    assert ds_viewset.filterset_fields == ["reader_study"], (
        "Please check DisplaySetViewSet's filter_queryset method and "
        "ensure shuffle order and index consistency are still intact."
    )


@pytest.mark.django_db
def test_query_unanswered_display_sets_for_another_user(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    editor, r1, r2 = UserFactory.create_batch(3)
    rs = ReaderStudyFactory()
    rs.add_editor(editor)
    rs.add_reader(r1)
    rs.add_reader(r2)
    assert editor.has_perm("change_readerstudy", rs)

    q1, q2 = (
        QuestionFactory(reader_study=rs, answer_type=Question.AnswerType.BOOL)
        for _ in range(2)
    )
    civ1, civ2 = (
        ComponentInterfaceValueFactory(image=ImageFactory()) for _ in range(2)
    )
    ds1, ds2 = (DisplaySetFactory(reader_study=rs) for _ in range(2))
    ds1.values.add(civ1)
    ds2.values.add(civ2)
    AnswerFactory(question=q1, display_set=ds1, creator=r1)
    AnswerFactory(question=q2, display_set=ds1, creator=r1)

    # R2 cannot retrieve unanswered ds from R1
    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={
            "reader_study": str(rs.pk),
            "unanswered_by_user": True,
            "user": r1.username,
        },
        user=r2,
        client=client,
        method=client.get,
    )
    assert response.status_code == 403

    # but R2 can retrieve their own unanswered display sets
    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={
            "reader_study": str(rs.pk),
            "unanswered_by_user": True,
            "user": r2.username,
        },
        user=r2,
        client=client,
        method=client.get,
    )
    assert response.json()["count"] == 2

    # the rs editor can view all
    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={
            "reader_study": str(rs.pk),
            "unanswered_by_user": True,
            "user": r1.username,
        },
        user=editor,
        client=client,
        method=client.get,
    )

    assert response.json()["count"] == 1

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={
            "reader_study": str(rs.pk),
            "unanswered_by_user": True,
            "user": r2.username,
        },
        user=editor,
        client=client,
        method=client.get,
    )

    assert response.json()["count"] == 2
