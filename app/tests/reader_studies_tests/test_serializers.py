import pytest

from grandchallenge.reader_studies.models import QuestionWidgetKindChoices
from grandchallenge.reader_studies.serializers import QuestionSerializer
from tests.reader_studies_tests.factories import QuestionFactory


@pytest.mark.django_db
def test_widget_on_question_serializer(rf):
    qu = QuestionFactory()
    serializer = QuestionSerializer(qu, context={"request": rf.get("/foo")})
    assert not serializer.data["widget"]
    qu.widget = QuestionWidgetKindChoices.ACCEPT_REJECT
    qu.save()
    serializer2 = QuestionSerializer(qu, context={"request": rf.get("/foo")})
    assert (
        serializer2.data["widget"]
        == QuestionWidgetKindChoices.ACCEPT_REJECT.label
    )
    assert serializer2.data["widget_options"] == {}
    qu.widget = QuestionWidgetKindChoices.NUMBER_INPUT
    qu.answer_min_value = 2
    qu.save()
    serializer3 = QuestionSerializer(qu, context={"request": rf.get("/foo")})
    assert (
        serializer3.data["widget"]
        == QuestionWidgetKindChoices.NUMBER_INPUT.label
    )
    assert serializer3.data["widget_options"] == {
        "answer_min_value": 2,
        "answer_max_value": None,
        "answer_step_size": None,
    }
