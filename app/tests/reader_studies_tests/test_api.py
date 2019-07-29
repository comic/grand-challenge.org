import pytest

from grandchallenge.reader_studies.models import Answer
from tests.factories import UserFactory, ImageFactory
from tests.reader_studies_tests.factories import (
    ReaderStudyFactory,
    QuestionFactory,
    AnswerFactory,
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
    a1, a2 = (
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

    q = QuestionFactory(reader_study=rs)

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
