import pytest

from tests.factories import UserFactory
from tests.reader_studies_tests.factories import (
    ReaderStudyFactory,
    QuestionFactory,
    AnswerFactory,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_api_list_is_filtered(client):
    user = UserFactory(is_staff=True)
    rs1, rs2 = ReaderStudyFactory(), ReaderStudyFactory()
    q1, q2 = (
        QuestionFactory(reader_study=rs1),
        QuestionFactory(reader_study=rs2),
    )
    a1, a2 = (
        AnswerFactory(question=q1, answer=True),
        AnswerFactory(question=q2, answer=False),
    )

    response = get_view_for_user(
        viewname="api:reader-study-list", user=user, client=client
    )
    assert response.status_code == 200
    assert response.json()["count"] == 2

    response = get_view_for_user(
        viewname="api:reader-study-detail",
        reverse_kwargs={"pk": rs1.pk},
        user=user,
        client=client,
    )
    assert response.status_code == 200
    assert len(response.json()["questions"]) == 1

    response = get_view_for_user(
        viewname="api:reader-study-questions-list",
        reverse_kwargs={"reader_study_pk": rs1.pk},
        user=user,
        client=client,
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["pk"] == str(q1.pk)

    response = get_view_for_user(
        viewname="api:reader-study-question-answers-list",
        reverse_kwargs={"reader_study_pk": rs1.pk, "question_pk": q1.pk},
        user=user,
        client=client,
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["pk"] == str(a1.pk)
