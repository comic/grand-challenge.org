from rest_framework.fields import CharField
from rest_framework.relations import SlugRelatedField, HyperlinkedRelatedField
from rest_framework.serializers import (
    HyperlinkedModelSerializer,
    ModelSerializer,
)
from rest_framework_nested.relations import NestedHyperlinkedIdentityField

from grandchallenge.reader_studies.models import ReaderStudy, Question, Answer


class QuestionSerializer(ModelSerializer):
    answer_type = CharField(source="get_answer_type_display")

    class Meta:
        model = Question
        fields = ("pk", "reader_study", "question_text", "answer_type")


class ReaderStudySerializer(HyperlinkedModelSerializer):
    creator = SlugRelatedField(read_only=True, slug_field="username")
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = ReaderStudy
        fields = (
            "pk",
            "title",
            "creator",
            "description",
            "is_valid",
            "questions",
            "hanging_list_images",
        )


class AnswerSerializer(HyperlinkedModelSerializer):
    creator = SlugRelatedField(read_only=True, slug_field="username")

    question = NestedHyperlinkedIdentityField(
        view_name="reader-study-questions-detail",
        lookup_url_kwarg="question_pk",
    )
    images = HyperlinkedRelatedField(
        many=True,
        read_only=True,  # TODO: Provide a queryset
        view_name="image-detail",
    )

    class Meta:
        model = Answer
        fields = ("pk", "creator", "question", "images", "answer")
