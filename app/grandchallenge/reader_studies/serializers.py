from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField
from rest_framework.relations import HyperlinkedRelatedField, SlugRelatedField
from rest_framework.serializers import (
    HyperlinkedModelSerializer,
    SerializerMethodField,
)

from grandchallenge.cases.models import Image
from grandchallenge.reader_studies.models import Answer, Question, ReaderStudy


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

        if not question.reader_study.is_reader(user=creator):
            raise ValidationError("This user is not a reader for this study.")

        if not question.is_answer_valid(answer=answer):
            raise ValidationError(
                f"You answer is not the correct type. "
                f"{question.get_answer_type_display()} expected, "
                f"{type(answer)} found."
            )

        if len(images) == 0:
            raise ValidationError(
                "You must specify the images that this answer corresponds to."
            )

        reader_study_images = question.reader_study.images.all()
        for im in images:
            if im not in reader_study_images:
                raise ValidationError(
                    f"Image {im} does not belong to this reader study."
                )

        if Answer.objects.filter(
            creator=creator, question=question, images__in=images
        ).exists():
            raise ValidationError(
                f"User {creator} has already answered this question "
                f"for at least 1 of these images."
            )

        return attrs

    class Meta:
        model = Answer
        fields = ("answer", "api_url", "creator", "images", "pk", "question")
