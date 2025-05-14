import pytest

from grandchallenge.reader_studies.interactive_algorithms import (
    InteractiveAlgorithmChoices,
)
from grandchallenge.reader_studies.models import QuestionWidgetKindChoices
from grandchallenge.reader_studies.serializers import QuestionSerializer
from tests.reader_studies_tests.factories import QuestionFactory


@pytest.mark.django_db
def test_widget_on_question_serializer(rf):
    qu = QuestionFactory()
    serializer = QuestionSerializer(qu, context={"request": rf.get("/foo")})
    assert serializer.data["widget"] == ""
    qu.widget = QuestionWidgetKindChoices.ACCEPT_REJECT
    qu.save()
    serializer2 = QuestionSerializer(qu, context={"request": rf.get("/foo")})
    assert (
        serializer2.data["widget"]
        == QuestionWidgetKindChoices.ACCEPT_REJECT.label
    )


@pytest.mark.django_db
def test_interactive_algorithm_on_question_serializer(rf):
    qu = QuestionFactory()
    serializer = QuestionSerializer(qu, context={"request": rf.get("/foo")})
    assert serializer.data["interactive_algorithms"] == []
    qu.interactive_algorithm = InteractiveAlgorithmChoices.ULS23_BASELINE
    qu.save()
    serializer2 = QuestionSerializer(qu, context={"request": rf.get("/foo")})
    assert serializer2.data["interactive_algorithms"] == ["uls23-baseline"]


@pytest.mark.django_db
def test_default_annotation_color_on_question_serializer(rf):
    qu = QuestionFactory()

    serializer = QuestionSerializer(qu, context={"request": rf.get("/foo")})
    assert serializer.data["default_annotation_color"] == ""

    qu.default_annotation_color = "#000000"
    qu.save()

    serializer2 = QuestionSerializer(qu, context={"request": rf.get("/foo")})
    assert serializer2.data["default_annotation_color"] == "#000000"
