from rest_framework.fields import CharField
from rest_framework.relations import HyperlinkedRelatedField, SlugRelatedField
from rest_framework.serializers import (
    HyperlinkedModelSerializer,
    SerializerMethodField,
)

from grandchallenge.api.swagger import swagger_schema_fields_for_charfield
from grandchallenge.cases.models import Image
from grandchallenge.reader_studies.models import (
    ANSWER_TYPE_SCHEMA,
    Answer,
    Question,
    ReaderStudy,
)


class QuestionSerializer(HyperlinkedModelSerializer):
    answer_type = CharField(source="get_answer_type_display")
    reader_study = HyperlinkedRelatedField(
        view_name="api:reader-study-detail", read_only=True
    )
    form_direction = CharField(source="get_direction_display")
    image_port = CharField(source="get_image_port_display")

    class Meta:
        model = Question
        fields = (
            "answer_type",
            "api_url",
            "form_direction",
            "help_text",
            "image_port",
            "pk",
            "question_text",
            "reader_study",
            "required",
        )
        swagger_schema_fields = swagger_schema_fields_for_charfield(
            answer_type=model._meta.get_field("answer_type"),
            form_direction=model._meta.get_field(
                "direction"
            ),  # model.direction gets remapped
            image_port=model._meta.get_field("image_port"),
        )


class ReaderStudySerializer(HyperlinkedModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    hanging_list_images = SerializerMethodField()

    class Meta:
        model = ReaderStudy
        fields = (
            "api_url",
            "description",
            "hanging_list_images",
            "is_valid",
            "pk",
            "questions",
            "title",
        )

    def get_hanging_list_images(self, obj: ReaderStudy):
        """Used by hanging_list_images serializer field."""
        return obj.get_hanging_list_images_for_user(
            user=self.context["request"].user
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

    def validate(self, attrs):
        question = attrs["question"]
        images = attrs["images"]
        answer = attrs["answer"]
        creator = self.context.get("request").user

        Answer.validate(
            creator=creator, question=question, answer=answer, images=images
        )
        return attrs

    class Meta:
        model = Answer
        fields = (
            "answer",
            "api_url",
            "created",
            "creator",
            "images",
            "pk",
            "question",
        )
        swagger_schema_fields = {
            "properties": {"answer": {"title": "Answer", **ANSWER_TYPE_SCHEMA}}
        }
