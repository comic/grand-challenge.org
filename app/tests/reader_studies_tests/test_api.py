import re
from pathlib import Path
from unittest import mock

import pytest
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.components.models import InterfaceKind
from grandchallenge.reader_studies.models import Answer, DisplaySet, Question
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

    rs = ReaderStudyFactory()
    rs.images.add(im)
    rs.save()

    reader = UserFactory()
    rs.add_reader(reader)

    q = QuestionFactory(reader_study=rs, answer_type=Question.AnswerType.BOOL)

    response = get_view_for_user(
        viewname="api:reader-studies-answer-list",
        user=reader,
        client=client,
        method=client.post,
        data={"answer": True, "images": [im.api_url], "question": q.api_url},
        content_type="application/json",
    )

    assert response.status_code == 201

    answer = Answer.objects.get(pk=response.data.get("pk"))

    assert answer.creator == reader
    assert answer.images.count() == 1
    assert answer.images.all()[0] == im
    assert answer.question == q
    assert answer.answer is True

    civ = ComponentInterfaceValueFactory(image=im)
    ds = DisplaySetFactory(reader_study=rs)
    ds.values.add(civ)

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
    im1, im2 = ImageFactory(), ImageFactory()

    rs = ReaderStudyFactory()
    rs.images.add(im1, im2)
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
        data={"answer": True, "images": [im1.api_url], "question": q.api_url},
        content_type="application/json",
    )
    assert response.status_code == 201

    answer = Answer.objects.get(pk=response.data.get("pk"))
    assert answer.answer is True
    assert answer.images.first() == im1
    assert answer.history.count() == 1

    response = get_view_for_user(
        viewname="api:reader-studies-answer-detail",
        reverse_kwargs={"pk": answer.pk},
        user=reader,
        client=client,
        method=client.patch,
        data={"answer": False, "images": [im2.api_url]},
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
    assert answer.images.first() == im1
    assert answer.history.count() == 1

    rs.allow_answer_modification = True
    rs.save()

    response = get_view_for_user(
        viewname="api:reader-studies-answer-detail",
        reverse_kwargs={"pk": answer.pk},
        user=reader,
        client=client,
        method=client.patch,
        data={"answer": False, "images": [im2.api_url]},
        content_type="application/json",
    )
    assert response.status_code == 400

    answer.refresh_from_db()
    assert response.json() == {
        "non_field_errors": ["Only the answer field can be modified."]
    }
    assert answer.answer is True
    assert answer.images.first() == im1
    assert answer.history.count() == 1

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
    assert answer.images.first() == im1
    assert answer.history.count() == 2

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
    assert answer.history.count() == 2


@pytest.mark.django_db
def test_answer_creator_is_reader(client):
    rs_set = TwoReaderStudies()

    im = ImageFactory()
    rs_set.rs1.images.add(im)

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
                "images": [im.api_url],
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
        (Question.AnswerType.SINGLE_LINE_TEXT, "dgfsgfds", 201),
        (Question.AnswerType.SINGLE_LINE_TEXT, True, 400),
        (Question.AnswerType.SINGLE_LINE_TEXT, 12, 400),
        (Question.AnswerType.MULTI_LINE_TEXT, "dgfsgfds", 201),
        (Question.AnswerType.MULTI_LINE_TEXT, True, 400),
        (Question.AnswerType.MULTI_LINE_TEXT, 12, 400),
        (Question.AnswerType.HEADING, True, 400),
        (Question.AnswerType.HEADING, "null", 400),
        (Question.AnswerType.HEADING, None, 400),
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
        (Question.AnswerType.SINGLE_LINE_TEXT, None, 400),
        (Question.AnswerType.MULTI_LINE_TEXT, None, 400),
        (Question.AnswerType.BOOL, None, 400),
        (Question.AnswerType.NUMBER, None, 400),
        (Question.AnswerType.HEADING, None, 400),
        (Question.AnswerType.BOUNDING_BOX_2D, None, 201),
        (Question.AnswerType.MULTIPLE_2D_BOUNDING_BOXES, None, 201),
        (Question.AnswerType.DISTANCE_MEASUREMENT, None, 201),
        (Question.AnswerType.MULTIPLE_DISTANCE_MEASUREMENTS, None, 201),
        (Question.AnswerType.POINT, None, 201),
        (Question.AnswerType.MULTIPLE_POINTS, None, 201),
        (Question.AnswerType.POLYGON, None, 201),
        (Question.AnswerType.MULTIPLE_POLYGONS, None, 201),
        (Question.AnswerType.CHOICE, None, 400),
        (Question.AnswerType.MULTIPLE_CHOICE, None, 400),
        (Question.AnswerType.MULTIPLE_CHOICE_DROPDOWN, None, 400),
    ),
)
def test_answer_is_correct_type(client, answer_type, answer, expected):
    im = ImageFactory()

    rs = ReaderStudyFactory()
    rs.images.add(im)
    rs.save()

    reader = UserFactory()
    rs.add_reader(reader)

    q = QuestionFactory(reader_study=rs, answer_type=answer_type)

    response = get_view_for_user(
        viewname="api:reader-studies-answer-list",
        user=reader,
        client=client,
        method=client.post,
        data={"answer": answer, "images": [im.api_url], "question": q.api_url},
        content_type="application/json",
    )
    assert response.status_code == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "answer_type", (Question.AnswerType.CHOICE, Question.AnswerType.NUMBER)
)
def test_only_non_required_can_be_null(client, answer_type):
    im = ImageFactory()
    rs = ReaderStudyFactory()
    rs.images.add(im)
    rs.save()
    reader = UserFactory()
    rs.add_reader(reader)

    q = QuestionFactory(
        reader_study=rs, answer_type=answer_type, required=True
    )

    response = get_view_for_user(
        viewname="api:reader-studies-answer-list",
        user=reader,
        client=client,
        method=client.post,
        data={"answer": None, "images": [im.api_url], "question": q.api_url},
        content_type="application/json",
    )
    assert response.status_code == 400

    q = QuestionFactory(
        reader_study=rs, answer_type=answer_type, required=False
    )

    response = get_view_for_user(
        viewname="api:reader-studies-answer-list",
        user=reader,
        client=client,
        method=client.post,
        data={"answer": None, "images": [im.api_url], "question": q.api_url},
        content_type="application/json",
    )
    assert response.status_code == 201


@pytest.mark.django_db
def test_mine(client):
    im1, im2 = ImageFactory(), ImageFactory()
    rs1, rs2 = ReaderStudyFactory(), ReaderStudyFactory()
    rs1.images.add(im1)
    rs2.images.add(im2)

    reader = UserFactory()
    rs1.add_reader(reader)
    rs2.add_reader(reader)

    q1 = QuestionFactory(
        reader_study=rs1, answer_type=Question.AnswerType.BOOL
    )
    q2 = QuestionFactory(
        reader_study=rs2, answer_type=Question.AnswerType.BOOL
    )

    a1 = AnswerFactory(question=q1, creator=reader, answer=True)
    a1.images.add(im1)

    a2 = AnswerFactory(question=q2, creator=reader, answer=True)
    a2.images.add(im2)

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
    im = ImageFactory()
    rs = ReaderStudyFactory()
    rs.images.add(im)

    editor = UserFactory()
    rs.add_editor(editor)
    rs.add_reader(editor)

    q = QuestionFactory(reader_study=rs, answer_type=Question.AnswerType.BOOL)

    a1 = AnswerFactory(
        question=q, creator=editor, answer=True, is_ground_truth=True
    )
    a1.images.add(im)

    a2 = AnswerFactory(
        question=q, creator=editor, answer=True, is_ground_truth=False
    )
    a2.images.add(im)

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
        (Question.AnswerType.SINGLE_LINE_TEXT, "dgfsgfds"),
        (Question.AnswerType.MULTI_LINE_TEXT, "dgfsgfds\ndgfsgfds"),
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
    im = ImageFactory()

    rs = ReaderStudyFactory()
    rs.images.add(im)
    rs.save()

    editor = UserFactory()
    rs.add_editor(editor)

    reader = UserFactory()
    rs.add_reader(reader)

    q = QuestionFactory(
        question_text="foo", reader_study=rs, answer_type=answer_type
    )

    a = AnswerFactory(question=q, answer=answer)
    a.images.add(im)
    a.save()

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
        viewname="api:image-list",
        params={"readerstudies": str(rs.pk)},
        user=editor,
        client=client,
        method=client.get,
        HTTP_ACCEPT="text/csv",
    )

    headers = str(response.serialize_headers())
    content = str(response.content)

    assert response.status_code == 200
    assert "Content-Type: text/csv" in headers

    assert im.name in content


@pytest.mark.django_db
@mock.patch(
    "grandchallenge.reader_studies.models.ReaderStudy.generate_hanging_list"
)
def test_generate_hanging_list_api_view(generate_hanging_list, client):
    rs = ReaderStudyFactory()
    editor = UserFactory()
    rs.add_editor(editor)

    response = get_view_for_user(
        viewname="api:reader-study-generate-hanging-list",
        reverse_kwargs={"pk": rs.pk},
        user=editor,
        client=client,
        method=client.patch,
        follow=True,
    )

    assert response.status_code == 200
    assert "Hanging list generated." in str(response.content)
    generate_hanging_list.assert_called_once()


@pytest.mark.django_db
def test_remove_image_api_view(client):
    rs = ReaderStudyFactory()
    reader, editor = UserFactory(), UserFactory()
    rs.add_reader(reader)
    rs.add_editor(editor)

    response = get_view_for_user(
        viewname="api:reader-study-remove-image",
        reverse_kwargs={"pk": rs.pk},
        user=reader,
        client=client,
        method=client.patch,
        data={"image": 1},
        content_type="application/json",
        follow=True,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        viewname="api:reader-study-remove-image",
        reverse_kwargs={"pk": rs.pk},
        user=editor,
        client=client,
        method=client.patch,
        data={"image": 1},
        content_type="application/json",
        follow=True,
    )

    assert response.status_code == 200
    assert "Image could not be removed from reader study." in str(
        response.content
    )

    im = ImageFactory()
    rs.images.add(im)

    assert im in rs.images.all()

    response = get_view_for_user(
        viewname="api:reader-study-remove-image",
        reverse_kwargs={"pk": rs.pk},
        user=editor,
        client=client,
        method=client.patch,
        data={"image": im.pk},
        content_type="application/json",
        follow=True,
    )

    assert response.status_code == 200
    assert "Image removed from reader study." in str(response.content)
    assert im not in rs.images.all()


@pytest.mark.django_db
def test_ground_truth(client):
    rs = ReaderStudyFactory(is_educational=True)
    reader = UserFactory()
    rs.add_reader(reader)

    q1 = QuestionFactory(
        answer_type=Question.AnswerType.CHOICE, reader_study=rs
    )
    q2 = QuestionFactory(
        answer_type=Question.AnswerType.MULTIPLE_CHOICE, reader_study=rs
    )
    q3 = QuestionFactory(
        answer_type=Question.AnswerType.MULTIPLE_CHOICE_DROPDOWN,
        reader_study=rs,
    )

    op1 = CategoricalOptionFactory(question=q1, title="option1")
    op2 = CategoricalOptionFactory(question=q2, title="option1")
    op3 = CategoricalOptionFactory(question=q2, title="option1")
    op4 = CategoricalOptionFactory(question=q3, title="option1")
    op5 = CategoricalOptionFactory(question=q3, title="option1")

    im = ImageFactory()
    rs.images.add(im)

    a1 = AnswerFactory(question=q1, answer=op1.pk, is_ground_truth=True)
    a1.images.add(im)

    a2 = AnswerFactory(
        question=q2, answer=[op2.pk, op3.pk], is_ground_truth=True
    )
    a2.images.add(im)

    a3 = AnswerFactory(
        question=q3, answer=[op4.pk, op5.pk], is_ground_truth=True
    )
    a3.images.add(im)

    response = get_view_for_user(
        viewname="api:reader-study-ground-truth",
        reverse_kwargs={"pk": rs.pk, "case_pk": im.pk},
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
@pytest.mark.parametrize("answer_type", ("MASK",))
def test_assign_answer_image(client, settings, answer_type):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    rs = ReaderStudyFactory()
    im = ImageFactory()
    editor, reader = UserFactory(), UserFactory()

    rs.images.add(im)
    rs.add_editor(editor)
    rs.add_reader(reader)

    question = QuestionFactory(reader_study=rs, answer_type=answer_type)

    # First post/patch the answer (ReaderStudyAnswersAPI in gcapi)
    response = get_view_for_user(
        viewname="api:reader-studies-answer-list",
        user=reader,
        client=client,
        method=client.post,
        data={
            "answer": None,  # Answer must be None to image assignment
            "images": [im.api_url],
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
        / "image10x10x10.mha",
        creator=reader,
    )
    with capture_on_commit_callbacks(execute=True):
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
    image = RawImageUploadSession.objects.get(
        pk=response.json()["pk"]
    ).image_set.first()

    assert answer.answer_image == image
    assert reader.has_perm("view_image", image)
    assert editor.has_perm("view_image", image)


@pytest.mark.django_db
@pytest.mark.parametrize("answer_type", ("MASK",))
def test_upload_session_owned_by_answer_creator(client, settings, answer_type):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    rs = ReaderStudyFactory()
    im = ImageFactory()
    editor, reader = UserFactory(), UserFactory()

    rs.images.add(im)
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
    im = ImageFactory()
    reader = UserFactory()

    rs.images.add(im)
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
def test_display_set_endpoints(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    r = UserFactory()

    rs1, rs2 = (ReaderStudyFactory(use_display_sets=True) for _ in range(2))
    rs1.add_reader(r)
    rs2.add_reader(r)
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
        user=r,
        client=client,
        method=client.get,
    )

    assert response.json()["count"] == 4

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={"reader_study": str(rs1.pk)},
        user=r,
        client=client,
        method=client.get,
    )

    assert response.json()["count"] == 2
    rs1.shuffle_hanging_list = True
    rs1.save()
    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={"reader_study": str(rs1.pk), "unanswered_by_user": True},
        user=r,
        client=client,
        method=client.get,
    )

    assert response.json()["count"] == 2

    AnswerFactory(question=q1, display_set=ds1, creator=r)

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={"reader_study": str(rs1.pk), "unanswered_by_user": True},
        user=r,
        client=client,
        method=client.get,
    )

    assert response.json()["count"] == 2

    AnswerFactory(question=q2, display_set=ds1, creator=r)

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        data={"reader_study": str(rs1.pk), "unanswered_by_user": True},
        user=r,
        client=client,
        method=client.get,
    )

    assert response.json()["count"] == 1


@pytest.mark.django_db
def test_display_set_shuffling(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    r1, r2 = UserFactory(), UserFactory()

    rs = ReaderStudyFactory(use_display_sets=True)
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
def test_display_set_add_and_edit(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    r1, r2 = UserFactory(), UserFactory()

    rs = ReaderStudyFactory(use_display_sets=True)
    rs.add_editor(r1)
    rs.add_reader(r2)

    response = get_view_for_user(
        viewname="api:reader-studies-display-set-list",
        user=r1,
        client=client,
        method=client.post,
        content_type="application/json",
        data={"reader_study": rs.slug},
    )

    ds = DisplaySet.objects.get(pk=response.json()["pk"])
    with capture_on_commit_callbacks(execute=True):
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

    with capture_on_commit_callbacks(execute=True):
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

    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.BOOL
    )

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

    # Create another display set
    ds2 = DisplaySetFactory(reader_study=rs)
    civ = ComponentInterfaceValueFactory(interface=ci, value=False)
    ds2.values.add(civ)

    assert ds2.values.count() == 1

    # Add the image civ to the new display set
    response = get_view_for_user(
        viewname="api:reader-studies-display-set-detail",
        reverse_kwargs={"pk": ds2.pk},
        user=r1,
        client=client,
        method=client.patch,
        content_type="application/json",
        data={"civ_values": [new.pk]},
    )

    ds.refresh_from_db()
    ds2.refresh_from_db()

    # The image civ is now part of both display sets
    assert ds.values.count() == 2
    assert ds2.values.count() == 2

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
    assert response.content.decode("utf-8") == (
        "This display set cannot be changed, as answers for it already exist."
    )
