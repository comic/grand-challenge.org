from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.fields import (
    BooleanField,
    CharField,
    DurationField,
    JSONField,
    ReadOnlyField,
    URLField,
)
from rest_framework.relations import HyperlinkedRelatedField, SlugRelatedField
from rest_framework.serializers import (
    HyperlinkedModelSerializer,
    ModelSerializer,
    SerializerMethodField,
)

from grandchallenge.components.schemas import ANSWER_TYPE_SCHEMA
from grandchallenge.components.serializers import (
    CIVSetPostSerializerMixin,
    ComponentInterfaceSerializer,
    HyperlinkedComponentInterfaceValueSerializer,
)
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.core.templatetags.bleach import clean
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
from grandchallenge.workstation_configs.serializers import (
    LookUpTableSerializer,
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
    interface = ComponentInterfaceSerializer(read_only=True, allow_null=True)
    look_up_table = LookUpTableSerializer(read_only=True, allow_null=True)
    widget = CharField(source="get_widget_display", read_only=True)
    interactive_algorithms = SerializerMethodField()
    question_text_safe = SerializerMethodField()
    help_text_safe = SerializerMethodField()
    empty_answer_confirmation_label_safe = SerializerMethodField()

    class Meta:
        model = Question
        fields = (
            "answer_type",
            "api_url",
            "form_direction",
            "help_text",  # Deprecated, remove after 2025.10
            "help_text_safe",  # Safe to use in rendered html
            "image_port",
            "default_annotation_color",
            "pk",
            "question_text",  # Deprecated, remove after 2025.10
            "question_text_safe",  # Safe to use in rendered html
            "reader_study",
            "required",
            "options",
            "interface",
            "overlay_segments",
            "look_up_table",
            "widget",
            "answer_min_value",
            "answer_max_value",
            "answer_step_size",
            "answer_min_length",
            "answer_max_length",
            "answer_match_pattern",
            "empty_answer_confirmation",
            "empty_answer_confirmation_label",  # Deprecated, remove after 2025.10
            "empty_answer_confirmation_label_safe",  # Safe to use in rendered html
            "interactive_algorithms",
        )

    def get_interactive_algorithms(self, obj) -> list[str]:
        # In the future we may allow many interactive
        # algorithms per question
        if obj.interactive_algorithm:
            return [obj.interactive_algorithm]
        else:
            return []

    def get_question_text_safe(self, obj) -> str:
        return clean(obj.question_text, no_tags=True)

    def get_help_text_safe(self, obj) -> str:
        return clean(obj.help_text, no_tags=False)

    def get_empty_answer_confirmation_label_safe(self, obj) -> str:
        return clean(obj.empty_answer_confirmation_label, no_tags=True)


class DisplaySetSerializer(HyperlinkedModelSerializer):
    reader_study = HyperlinkedRelatedField(
        view_name="api:reader-study-detail", read_only=True
    )
    values = HyperlinkedComponentInterfaceValueSerializer(many=True)
    hanging_protocol = HangingProtocolSerializer(
        source="reader_study.hanging_protocol", read_only=True, allow_null=True
    )
    optional_hanging_protocols = HangingProtocolSerializer(
        many=True,
        source="reader_study.optional_hanging_protocols",
        read_only=True,
        required=False,
    )
    view_content = JSONField(
        source="reader_study.view_content", read_only=True
    )
    index = SerializerMethodField()
    title_safe = SerializerMethodField()

    def get_index(self, obj) -> int | None:
        if obj.reader_study.shuffle_hanging_list:
            try:
                return self.context["view"].randomized_qs.index(obj)
            except ValueError:
                # The list is empty if no reader study is specified.
                return None
        else:
            return obj.standard_index

    def get_title_safe(self, obj) -> str:
        return clean(obj.title, no_tags=True)

    class Meta:
        model = DisplaySet
        fields = (
            "pk",
            "title",  # Can be set by users
            "title_safe",  # Safe to use in rendered html
            "reader_study",
            "values",
            "order",
            "api_url",
            "hanging_protocol",
            "optional_hanging_protocols",
            "view_content",
            "description",
            "index",
        )


class DisplaySetPostSerializer(
    CIVSetPostSerializerMixin,
    DisplaySetSerializer,
):
    editability_error_message = (
        "This display set cannot be changed, as answers for it already exist."
    )
    reader_study = SlugRelatedField(
        slug_field="slug", queryset=ReaderStudy.objects.none(), required=False
    )

    def create(self, validated_data):
        if validated_data.pop("values", []) != []:
            raise DRFValidationError("Values can only be added via update")
        return super().create(validated_data)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "request" in self.context:
            user = self.context["request"].user
            self.fields["reader_study"].queryset = filter_by_permission(
                queryset=ReaderStudy.objects.all(),
                user=user,
                codename="change_readerstudy",
            )


class ReaderStudySerializer(HyperlinkedModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    help_text = ReadOnlyField()
    logo = URLField(source="logo.x20.url", read_only=True)
    url = URLField(source="get_absolute_url", read_only=True)
    title_safe = SerializerMethodField()

    def get_title_safe(self, obj) -> str:
        return clean(obj.title, no_tags=True)

    class Meta:
        model = ReaderStudy
        fields = (
            "api_url",
            "url",
            "slug",
            "logo",
            "description",
            "help_text",  # Deprecated, remove after 2025.10
            "help_text_safe",  # Safe to use in rendered html
            "pk",
            "questions",
            "title",  # Deprecated, remove after 2025.10
            "title_safe",  # Safe to use in rendered html
            "is_educational",
            "instant_verification",
            "has_ground_truth",
            "allow_answer_modification",
            "enable_autosaving",
            "allow_case_navigation",
            "allow_show_all_annotations",
            "roll_over_answers_for_n_cases",
            "end_of_study_text_safe",
        )


class AnswerSerializer(HyperlinkedModelSerializer):
    creator = SlugRelatedField(read_only=True, slug_field="username")
    question = HyperlinkedRelatedField(
        view_name="api:reader-studies-question-detail",
        queryset=Question.objects.all(),
    )
    display_set = HyperlinkedRelatedField(
        queryset=DisplaySet.objects.all(),
        view_name="api:reader-studies-display-set-detail",
        required=False,
    )
    answer_image = HyperlinkedRelatedField(
        read_only=True,
        view_name="api:image-detail",
        allow_null=True,
    )
    total_edit_duration = DurationField(
        read_only=True,
        allow_null=True,
    )
    # At the moment only non-ground-truth answers are created over REST
    is_ground_truth = BooleanField(read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "request" in self.context:
            user = self.context["request"].user
            self.fields["display_set"].queryset = filter_by_permission(
                queryset=DisplaySet.objects.all(),
                user=user,
                codename="view_displayset",
            )

    def validate(self, attrs):
        answer = attrs.get("answer")
        last_edit_duration = attrs.get("last_edit_duration")
        if self.instance:
            if (
                not self.instance.question.reader_study.allow_answer_modification
            ):
                raise ValidationError(
                    "This reader study does not allow answer modification."
                )
            if not set(attrs.keys()).issubset(
                {"answer", "last_edit_duration"}
            ):
                raise ValidationError(
                    "Only the answer and last_edit_duration field can be modified."
                )
            question = self.instance.question
            display_set = self.instance.display_set
            creator = self.instance.creator
        else:
            question = attrs.get("question")
            display_set = attrs.get("display_set")
            creator = self.context.get("request").user

        Answer.validate(
            creator=creator,
            question=question,
            answer=answer,
            display_set=display_set,
            instance=self.instance,
        )

        return (
            attrs
            if not self.instance
            else {"answer": answer, "last_edit_duration": last_edit_duration}
        )

    class Meta:
        model = Answer
        fields = (
            "answer",
            "api_url",
            "created",
            "creator",
            "display_set",
            "pk",
            "question",
            "modified",
            "answer_image",
            "last_edit_duration",
            "total_edit_duration",
            "is_ground_truth",
        )
        swagger_schema_fields = {
            "properties": {"answer": {"title": "Answer", **ANSWER_TYPE_SCHEMA}}
        }
