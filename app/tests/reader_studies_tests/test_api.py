import csv
import re
from unittest import mock

import pytest

from grandchallenge.reader_studies.models import Answer, Question
from grandchallenge.reader_studies.views import ExportCSVMixin
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.reader_studies_tests.utils import TwoReaderStudies
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

    q = QuestionFactory(reader_study=rs, answer_type=Question.ANSWER_TYPE_BOOL)

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


@pytest.mark.django_db
def test_answer_creator_is_reader(client):
    rs_set = TwoReaderStudies()

    im = ImageFactory()
    rs_set.rs1.images.add(im)

    q = QuestionFactory(
        reader_study=rs_set.rs1, answer_type=Question.ANSWER_TYPE_BOOL
    )

    tests = (
        (rs_set.editor1, 403),
        (rs_set.reader1, 201),
        (rs_set.editor2, 403),
        (rs_set.reader2, 400),  # 400 as the check is done in validation
        (rs_set.u, 403),
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
        (Question.ANSWER_TYPE_BOOL, True, 201),
        (Question.ANSWER_TYPE_BOOL, "True", 400),
        (Question.ANSWER_TYPE_SINGLE_LINE_TEXT, "dgfsgfds", 201),
        (Question.ANSWER_TYPE_SINGLE_LINE_TEXT, True, 400),
        (Question.ANSWER_TYPE_MULTI_LINE_TEXT, "dgfsgfds", 201),
        (Question.ANSWER_TYPE_MULTI_LINE_TEXT, True, 400),
        (Question.ANSWER_TYPE_HEADING, True, 400),
        (Question.ANSWER_TYPE_HEADING, "null", 400),
        (Question.ANSWER_TYPE_HEADING, None, 400),
        (Question.ANSWER_TYPE_2D_BOUNDING_BOX, "", 400),
        (Question.ANSWER_TYPE_2D_BOUNDING_BOX, True, 400),
        (Question.ANSWER_TYPE_2D_BOUNDING_BOX, False, 400),
        (Question.ANSWER_TYPE_2D_BOUNDING_BOX, 134, 400),
        (Question.ANSWER_TYPE_2D_BOUNDING_BOX, "dsfuag", 400),
        (Question.ANSWER_TYPE_2D_BOUNDING_BOX, {}, 400),
        (
            Question.ANSWER_TYPE_2D_BOUNDING_BOX,
            {
                "version": {"major": 1, "minor": 0},
                "type": "2D bounding box",
                "name": "test_name",
                "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 0, 0]],
            },
            201,
        ),
        (
            Question.ANSWER_TYPE_2D_BOUNDING_BOX,
            {
                "type": "2D bounding box",
                "name": "test_name",
                "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 0, 0]],
            },
            400,
        ),
        (
            Question.ANSWER_TYPE_2D_BOUNDING_BOX,
            {
                "version": {"major": 1, "minor": 0},
                "name": "test_name",
                "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 0, 0]],
            },
            400,
        ),
        (
            Question.ANSWER_TYPE_2D_BOUNDING_BOX,
            '{"version": {"major": 1, "minor": 0}, "type": "2D bounding box", "name": "test_name", "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 0, 0]]}',
            400,
        ),  # Valid json, but a string
        (
            Question.ANSWER_TYPE_DISTANCE_MEASUREMENT,
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
            Question.ANSWER_TYPE_DISTANCE_MEASUREMENT,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Distance measurement",
                "name": "test",
                "end": (4, 5, 6),
            },
            400,
        ),
        (
            Question.ANSWER_TYPE_MULTIPLE_DISTANCE_MEASUREMENTS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple distance measurements",
                "lines": [{"start": (1, 2, 3), "end": (4, 5, 6)}],
            },
            201,
        ),
        (
            Question.ANSWER_TYPE_MULTIPLE_DISTANCE_MEASUREMENTS,
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
            Question.ANSWER_TYPE_MULTIPLE_DISTANCE_MEASUREMENTS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple distance measurements",
                "name": "test",
                "lines": [{"start": (1, 2, 3), "end": (4, 5, 6)}],
            },
            201,
        ),
        (
            Question.ANSWER_TYPE_MULTIPLE_DISTANCE_MEASUREMENTS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Distance measurements",
                "name": "test",
                "lines": [{"start": (1, 2, 3), "end": (4, 5, 6)}],
            },
            400,
        ),
        (
            Question.ANSWER_TYPE_MULTIPLE_DISTANCE_MEASUREMENTS,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Multiple distance measurements",
                "name": "test",
                "lines": [{"start": (1, 2, 3)}],
            },
            400,
        ),
        (
            Question.ANSWER_TYPE_MULTIPLE_DISTANCE_MEASUREMENTS,
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
            Question.ANSWER_TYPE_MULTIPLE_DISTANCE_MEASUREMENTS,
            {
                "type": "Multiple distance measurements",
                "lines": [{"start": (1, 2, 3), "end": (4, 5, 6)}],
            },
            400,
        ),
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
    "answer_type,answer",
    (
        (Question.ANSWER_TYPE_BOOL, True),
        (Question.ANSWER_TYPE_SINGLE_LINE_TEXT, "dgfsgfds"),
        (Question.ANSWER_TYPE_MULTI_LINE_TEXT, "dgfsgfds\ndgfsgfds"),
        (
            Question.ANSWER_TYPE_2D_BOUNDING_BOX,
            {
                "version": {"major": 1, "minor": 0},
                "type": "2D bounding box",
                "name": "test_name",
                "corners": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 0, 0]],
            },
        ),
        (
            Question.ANSWER_TYPE_DISTANCE_MEASUREMENT,
            {
                "version": {"major": 1, "minor": 0},
                "type": "Distance measurement",
                "name": "test",
                "start": (1, 2, 3),
                "end": (4, 5, 6),
            },
        ),
        (
            Question.ANSWER_TYPE_MULTIPLE_DISTANCE_MEASUREMENTS,
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
        viewname="api:reader-study-export-answers",
        reverse_kwargs={"pk": rs.pk},
        user=editor,
        client=client,
        method=client.get,
        content_type="application/json",
    )

    headers = str(response.serialize_headers())
    content = str(response.content)

    assert response.status_code == 200
    assert "Content-Type: text/csv" in headers
    assert f'filename="{rs.slug}-answers.csv"' in headers
    assert a.question.question_text in content
    assert a.question.get_answer_type_display() in content
    assert str(a.question.required) in content
    assert a.question.get_image_port_display() in content
    if isinstance(answer, dict):
        for key in answer:
            assert key in content
    else:
        assert re.sub(r"[\n\r\t]", " ", str(a.answer)) in content
    assert im.name in content
    assert a.creator.username in content

    response = get_view_for_user(
        viewname="api:reader-study-export-answers",
        reverse_kwargs={"pk": rs.pk},
        user=reader,
        client=client,
        method=client.get,
        content_type="application/json",
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "data,elements,lines",
    (
        ([["a"], ["b"], ["c"]], 1, 3),
        ([["a"], ["b,c"], ["c"]], 1, 3),
        ([["a\nb"], ["b"], ["c"]], 1, 3),
        ([["a\rb\nc", "\nb", "\rc\r\r"]], 3, 1),
        ([["a", "a", "\na"], ["b", "b", "b"], ["c", "c", "c"]], 3, 3),
        (
            [["a", '{"a":\n{"b": "c\nd"}\n}'], ["b", "b,c,d"], ["c", "d\r"]],
            2,
            3,
        ),
    ),
)
def test_csv_export_preprocessing(tmp_path, data, elements, lines):
    exporter = ExportCSVMixin()
    processed = exporter._preprocess_data(data)
    assert len(processed) == lines

    # Unfortunately, we have to create an actual file here, as both tempfile
    # and StringIO seem to cause issues with line endings
    with open(tmp_path / "csv.csv", "w+", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(processed)

    with open(tmp_path / "csv.csv", "r", newline="") as f:
        reader = csv.reader(f)
        for line in reader:
            assert len(line) == elements
        assert reader.line_num == lines


def test_csv_export_create_dicts():
    exporter = ExportCSVMixin()
    headers = ["foo", "bar"]
    data = []

    for x in range(10):
        data.append([f"foo{x}", f"bar{x}"])

    csv_dicts = exporter._create_dicts(headers, data)

    for index, dct in enumerate(csv_dicts):
        assert dct == {"foo": f"foo{index}", "bar": f"bar{index}"}


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
