import io

import pytest

from grandchallenge.reader_studies.models import Answer, Question
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
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
            answer_type=Question.ANSWER_TYPE_BOOL,
        ),
        QuestionFactory(
            reader_study=rs,
            question_text="q2",
            answer_type=Question.ANSWER_TYPE_CHOICE,
        ),
        QuestionFactory(
            reader_study=rs,
            question_text="q3",
            answer_type=Question.ANSWER_TYPE_SINGLE_LINE_TEXT,
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
