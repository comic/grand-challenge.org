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
    question = HyperlinkedRelatedField(
        view_name="api:reader-studies-question-detail", read_only=True
    )
    images = HyperlinkedRelatedField(
        many=True, queryset=Image.objects.all(), view_name="api:image-detail"
    )

    class Meta:
        model = Answer
        fields = ("pk", "creator", "images", "answer", "question")
