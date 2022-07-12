from django.core.exceptions import ValidationError
from django.db.transaction import on_commit
from guardian.shortcuts import get_objects_for_user
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
    ComponentInterfaceSerializer,
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
from grandchallenge.reader_studies.tasks import add_scores_for_display_set
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
    interface = ComponentInterfaceSerializer(read_only=True)
    look_up_table = LookUpTableSerializer(read_only=True)

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
            "interface",
            "overlay_segments",
            "look_up_table",
        )


class DisplaySetSerializer(HyperlinkedModelSerializer):
    reader_study = HyperlinkedRelatedField(
        view_name="api:reader-study-detail", read_only=True
    )
    values = HyperlinkedComponentInterfaceValueSerializer(many=True)
    hanging_protocol = HangingProtocolSerializer(
        source="reader_study.hanging_protocol", read_only=True
    )
    view_content = JSONField(
        source="reader_study.view_content", read_only=True
    )
    index = SerializerMethodField()

    def get_index(self, obj):
        if obj.reader_study.shuffle_hanging_list:
            try:
                return self.context["view"].randomized_qs.index(obj)
            except ValueError:
                # The list is empty if no reader study is specified.
                return None
        else:
            return obj.standard_index

    class Meta:
        model = DisplaySet
        fields = (
            "pk",
            "reader_study",
            "values",
            "order",
            "api_url",
            "hanging_protocol",
            "view_content",
            "description",
            "index",
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
    help_text = ReadOnlyField()
    logo = URLField(source="logo.x20.url", read_only=True)
    url = URLField(source="get_absolute_url", read_only=True)

    class Meta:
        model = ReaderStudy
        fields = (
            "api_url",
            "url",
            "slug",
            "logo",
            "description",
            "help_text",
            "pk",
            "questions",
            "title",
            "is_educational",
            "has_ground_truth",
            "allow_answer_modification",
            "allow_case_navigation",
            "allow_show_all_annotations",
            "roll_over_answers_for_n_cases",
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
        read_only=True, view_name="api:image-detail"
    )
    total_edit_duration = DurationField(read_only=True)
    # At the moment only non-ground-truth answers are created over REST
    is_ground_truth = BooleanField(read_only=True)

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

        if self.instance:
            on_commit(
                lambda: add_scores_for_display_set.apply_async(
                    kwargs={
                        "instance_pk": str(self.instance.pk),
                        "ds_pk": display_set.pk,
                    }
                )
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
