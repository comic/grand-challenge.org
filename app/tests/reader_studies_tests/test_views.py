import io

import pytest

from grandchallenge.reader_studies.models import Answer, Question
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
    AnswerFactory,
    CategoricalOptionFactory,
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_example_ground_truth(client, tmpdir):
    rs = ReaderStudyFactory()
    reader, editor = UserFactory(), UserFactory()
    q1, q2, q3 = (
        QuestionFactory(
            reader_study=rs,
            question_text="q1",
            answer_type=Question.AnswerType.BOOL,
        ),
        QuestionFactory(
            reader_study=rs,
            question_text="q2",
            answer_type=Question.AnswerType.CHOICE,
        ),
        QuestionFactory(
            reader_study=rs,
            question_text="q3",
            answer_type=Question.AnswerType.SINGLE_LINE_TEXT,
        ),
    )
    CategoricalOptionFactory(question=q2, title="option")
    im1, im2, im3 = (ImageFactory(), ImageFactory(), ImageFactory())
    rs.images.set([im1, im2, im3])
    rs.add_reader(reader)
    rs.add_editor(editor)
    rs.generate_hanging_list()

    response = get_view_for_user(
        viewname="reader-studies:example-ground-truth",
        client=client,
        method=client.get,
        reverse_kwargs={"slug": rs.slug},
        follow=True,
        user=reader,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:example-ground-truth",
        client=client,
        method=client.get,
        reverse_kwargs={"slug": rs.slug},
        follow=True,
        user=editor,
    )
    assert response.status_code == 200
    assert Answer.objects.count() == 0

    gt = io.BytesIO()
    gt.write(response.content)
    gt.seek(0)
    response = get_view_for_user(
        viewname="reader-studies:add-ground-truth",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        follow=True,
        data={"ground_truth": gt},
        user=editor,
    )
    assert response.status_code == 200
    assert Answer.objects.count() == rs.images.count() * rs.questions.count()
    for image in [im1, im2, im3]:
        for question in [q1, q2, q3]:
            assert Answer.objects.filter(
                images=image, question=question, is_ground_truth=True
            ).exists()


@pytest.mark.django_db
def test_answer_remove(client):
    rs = ReaderStudyFactory()
    r1, r2, editor = UserFactory(), UserFactory(), UserFactory()
    rs.add_reader(r1)
    rs.add_reader(r2)
    rs.add_editor(editor)
    q = QuestionFactory(
        reader_study=rs,
        question_text="q1",
        answer_type=Question.AnswerType.BOOL,
    )
    im = ImageFactory()
    a1 = AnswerFactory(creator=r1, question=q, answer=True)
    a1.images.set([im])
    a2 = AnswerFactory(creator=r2, question=q, answer=True)
    a2.images.set([im])
    assert Answer.objects.count() == 2

    response = get_view_for_user(
        viewname="reader-studies:answers-remove",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        data={"user": r1.id},
        follow=True,
        user=r1,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:answers-remove",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        data={"user": r1.id},
        follow=True,
        user=editor,
    )

    assert response.status_code == 200
    assert Answer.objects.count() == 1
    assert Answer.objects.filter(creator=r1).count() == 0
    assert Answer.objects.filter(creator=r2).count() == 1


@pytest.mark.django_db
def test_question_delete(client):
    rs = ReaderStudyFactory()
    r1, editor = UserFactory(), UserFactory()
    rs.add_reader(r1)
    rs.add_editor(editor)
    q = QuestionFactory(
        reader_study=rs,
        question_text="q1",
        answer_type=Question.AnswerType.BOOL,
    )
    assert Question.objects.count() == 1

    response = get_view_for_user(
        viewname="reader-studies:question-delete",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug, "pk": q.pk},
        follow=True,
        user=r1,
    )

    assert response.status_code == 403

    response = get_view_for_user(
        viewname="reader-studies:question-delete",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug, "pk": q.pk},
        user=editor,
    )

    assert response.status_code == 302
    assert Question.objects.count() == 0
    assert str(rs) in response.url


@pytest.mark.django_db
def test_question_delete_disabled_for_questions_with_answers(client):
    rs = ReaderStudyFactory()
    r1, editor = UserFactory(), UserFactory()
    rs.add_reader(r1)
    rs.add_editor(editor)
    q = QuestionFactory(
        reader_study=rs,
        question_text="q1",
        answer_type=Question.AnswerType.BOOL,
    )
    AnswerFactory(creator=r1, question=q, answer=True)

    assert Answer.objects.count() == 1
    assert Question.objects.count() == 1
    assert not q.is_fully_editable

    response = get_view_for_user(
        viewname="reader-studies:question-delete",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug, "pk": q.pk},
        user=editor,
    )

    assert response.status_code == 403
    assert Question.objects.count() == 1

    # if answer is deleted, deletion of the question is possible again
    get_view_for_user(
        viewname="reader-studies:answers-remove",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug},
        data={"user": r1.id},
        follow=True,
        user=editor,
    )

    assert Answer.objects.count() == 0

    response = get_view_for_user(
        viewname="reader-studies:question-delete",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": rs.slug, "pk": q.pk},
        user=editor,
    )
    assert response.status_code == 302
    assert Question.objects.count() == 0


@pytest.mark.django_db
def test_reader_study_list_view_filter(client):
    user = UserFactory()
    rs1, rs2, pubrs = (
        ReaderStudyFactory(),
        ReaderStudyFactory(),
        ReaderStudyFactory(public=True),
    )
    rs1.add_reader(user)

    response = get_view_for_user(
        viewname="reader-studies:list", client=client, user=user
    )

    assert response.status_code == 200
    assert rs1.get_absolute_url() in response.rendered_content
    assert rs2.get_absolute_url() not in response.rendered_content
    assert pubrs.get_absolute_url() in response.rendered_content
