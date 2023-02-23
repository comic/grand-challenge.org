import pytest

from grandchallenge.reader_studies.models import AnswerWidgetKindChoices
from grandchallenge.reader_studies.serializers import QuestionSerializer
from tests.reader_studies_tests.factories import (
    AnswerWidgetFactory,
    QuestionFactory,
)


@pytest.mark.django_db
def test_answer_widget_on_question_serializer(rf):
    qu = QuestionFactory()
    serializer = QuestionSerializer(qu, context={"request": rf.get("/foo")})
    assert not serializer.data["answer_widget"]
    qu.answer_widget = AnswerWidgetFactory(
        kind=AnswerWidgetKindChoices.ACCEPT_REJECT
    )
    qu.save()
    serializer2 = QuestionSerializer(qu, context={"request": rf.get("/foo")})
    assert serializer2.data["answer_widget"] == {
        "kind": AnswerWidgetKindChoices.ACCEPT_REJECT.label
    }
