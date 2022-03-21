from django.core.exceptions import ValidationError
from django.db.transaction import on_commit
from guardian.shortcuts import get_objects_for_user
from rest_framework.fields import CharField, ReadOnlyField, URLField
from rest_framework.relations import HyperlinkedRelatedField, SlugRelatedField
from rest_framework.serializers import (
    HyperlinkedModelSerializer,
    ModelSerializer,
    SerializerMethodField,
)

from grandchallenge.cases.models import Image
from grandchallenge.components.schemas import ANSWER_TYPE_SCHEMA
from grandchallenge.components.serializers import (
    ComponentInterfaceValuePostSerializer,
    HyperlinkedComponentInterfaceValueSerializer,
)
from grandchallenge.hanging_protocols.serializers import (
    HangingProtocolSerializer,
)
from grandchallenge.reader_studies.models import (
    Answer,
    CategoricalOption,
    DisplaySet,
    Question,
    ReaderStudy,
)
from grandchallenge.reader_studies.tasks import (
    add_scores,
    add_scores_for_display_set,
)


class CategoricalOptionSerializer(ModelSerializer):
    class Meta:
        model = CategoricalOption
        fields = ("id", "title", "default")


class QuestionSerializer(HyperlinkedModelSerializer):
    answer_type = CharField(source="get_answer_type_display", read_only=True)
    reader_study = HyperlinkedRelatedField(
        view_name="api:reader-study-detail", read_only=True
    )
    form_direction = CharField(source="get_direction_display", read_only=True)
    image_port = CharField(source="get_image_port_display", read_only=True)
    options = CategoricalOptionSerializer(many=True, read_only=True)

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
            "options",
        )


class DisplaySetSerializer(HyperlinkedModelSerializer):
    reader_study = HyperlinkedRelatedField(
        view_name="api:reader-study-detail", read_only=True
    )
    values = HyperlinkedComponentInterfaceValueSerializer(many=True)

    class Meta:
        model = DisplaySet
        fields = (
            "pk",
            "reader_study",
            "values",
            "order",
        )


class DisplaySetPostSerializer(DisplaySetSerializer):
    reader_study = SlugRelatedField(
        slug_field="slug", queryset=ReaderStudy.objects.none(), required=False
    )
    values = ComponentInterfaceValuePostSerializer(many=True, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "request" in self.context:
            user = self.context["request"].user
            self.fields["reader_study"].queryset = get_objects_for_user(
                user,
                "reader_studies.change_readerstudy",
                accept_global_perms=False,
            )
            self.fields["values"].queryset = get_objects_for_user(
                user,
                "reader_studies.change_displayset",
                accept_global_perms=False,
            )


class ReaderStudySerializer(HyperlinkedModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    hanging_list_images = SerializerMethodField()
    help_text = ReadOnlyField()
    case_text = ReadOnlyField(source="cleaned_case_text")
    logo = URLField(source="logo.x20.url", read_only=True)
    url = URLField(source="get_absolute_url", read_only=True)
    hanging_protocol = HangingProtocolSerializer()

    class Meta:
        model = ReaderStudy
        fields = (
            "api_url",
            "url",
            "slug",
            "logo",
            "description",
            "help_text",
            "hanging_list_images",
            "is_valid",
            "pk",
            "questions",
            "title",
            "is_educational",
            "has_ground_truth",
            "case_text",
            "allow_answer_modification",
            "allow_case_navigation",
            "allow_show_all_annotations",
            "roll_over_answers_for_n_cases",
            "use_display_sets",
            "hanging_protocol",
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
        many=True,
        queryset=Image.objects.all(),
        view_name="api:image-detail",
        required=False,
    )
    display_set = HyperlinkedRelatedField(
        queryset=DisplaySet.objects.all(),
        view_name="api:reader-studies-display-set-detail",
        required=False,
    )
    answer_image = HyperlinkedRelatedField(
        read_only=True, view_name="api:image-detail"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "request" in self.context:
            user = self.context["request"].user
            self.fields["display_set"].queryset = get_objects_for_user(
                user,
                "reader_studies.view_displayset",
                accept_global_perms=False,
            )

    def validate(self, attrs):
        answer = attrs.get("answer")
        if self.instance:
            if (
                not self.instance.question.reader_study.allow_answer_modification
            ):
                raise ValidationError(
                    "This reader study does not allow answer modification."
                )
            if list(attrs.keys()) != ["answer"]:
                raise ValidationError("Only the answer field can be modified.")
            question = self.instance.question
            images = self.instance.images.all()
            display_set = self.instance.display_set
            creator = self.instance.creator
        else:
            question = attrs.get("question")
            images = attrs.get("images")
            display_set = attrs.get("display_set")
            creator = self.context.get("request").user
        Answer.validate(
            creator=creator,
            question=question,
            answer=answer,
            images=images,
            display_set=display_set,
            instance=self.instance,
        )

        if self.instance:
            if images is not None and images.count() > 0:
                on_commit(
                    lambda: add_scores.apply_async(
                        kwargs={
                            "instance_pk": str(self.instance.pk),
                            "pk_set": list(
                                map(str, images.values_list("pk", flat=True))
                            ),
                        }
                    )
                )
            if display_set is not None:
                on_commit(
                    lambda: add_scores_for_display_set.apply_async(
                        kwargs={
                            "instance_pk": str(self.instance.pk),
                            "ds_pk": display_set.pk,
                        }
                    )
                )
        return attrs if not self.instance else {"answer": answer}

    class Meta:
        model = Answer
        fields = (
            "answer",
            "api_url",
            "created",
            "creator",
            "images",
            "display_set",
            "pk",
            "question",
            "modified",
            "answer_image",
        )
        swagger_schema_fields = {
            "properties": {"answer": {"title": "Answer", **ANSWER_TYPE_SCHEMA}}
        }
