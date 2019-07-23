from rest_framework.fields import CharField
from rest_framework.relations import SlugRelatedField, HyperlinkedRelatedField
from rest_framework.serializers import HyperlinkedModelSerializer

from grandchallenge.cases.models import Image
from grandchallenge.reader_studies.models import ReaderStudy, Question, Answer


class QuestionSerializer(HyperlinkedModelSerializer):
    answer_type = CharField(source="get_answer_type_display")
    reader_study = HyperlinkedRelatedField(
        view_name="api:reader-study-detail", read_only=True
    )

    class Meta:
        model = Question
        fields = (
            "answer_type",
            "api_url",
            "pk",
            "question_text",
            "reader_study",
        )


class ReaderStudySerializer(HyperlinkedModelSerializer):
    creator = SlugRelatedField(read_only=True, slug_field="username")
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = ReaderStudy
        fields = (
            "api_url",
            "creator",
            "description",
            "hanging_list_images",
            "is_valid",
            "pk",
            "questions",
            "title",
        )


class AnswerSerializer(HyperlinkedModelSerializer):
    creator = SlugRelatedField(read_only=True, slug_field="username")
    question = HyperlinkedRelatedField(
        view_name="api:reader-studies-question-detail",
        queryset=Question.objects.all(),
    )
    images = HyperlinkedRelatedField(
        many=True, queryset=Image.objects.all(), view_name="api:image-detail"
    )

    class Meta:
        model = Answer
        fields = ("answer", "api_url", "creator", "images", "pk", "question")
