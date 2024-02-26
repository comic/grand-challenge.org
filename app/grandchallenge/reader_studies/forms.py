import csv
import io
import json
import logging

from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    HTML,
    ButtonHolder,
    Div,
    Field,
    Fieldset,
    Layout,
    Submit,
)
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import BLANK_CHOICE_DASH
from django.forms import (
    BooleanField,
    CharField,
    ChoiceField,
    FileField,
    Form,
    IntegerField,
    ModelChoiceField,
    ModelForm,
    Select,
    Textarea,
    TextInput,
)
from django.forms.models import inlineformset_factory
from django.utils.text import format_lazy
from django_select2.forms import Select2MultipleWidget
from dynamic_forms import DynamicField, DynamicFormMixin

from grandchallenge.components.forms import MultipleCIVForm
from grandchallenge.components.models import ComponentInterface
from grandchallenge.core.forms import (
    PermissionRequestUpdateForm,
    SaveFormInitMixin,
    WorkstationUserFilterMixin,
)
from grandchallenge.core.layout import Formset
from grandchallenge.core.widgets import (
    ColorEditorWidget,
    JSONEditorWidget,
    MarkdownEditorWidget,
)
from grandchallenge.groups.forms import UserGroupForm
from grandchallenge.hanging_protocols.models import VIEW_CONTENT_SCHEMA
from grandchallenge.reader_studies.models import (
    ANSWER_TYPE_TO_INTERFACE_KIND_MAP,
    ANSWER_TYPE_TO_QUESTION_WIDGET_CHOICES,
    CASE_TEXT_SCHEMA,
    Answer,
    AnswerType,
    CategoricalOption,
    Question,
    ReaderStudy,
    ReaderStudyPermissionRequest,
)
from grandchallenge.subdomains.utils import reverse_lazy
from grandchallenge.workstation_configs.models import OVERLAY_SEGMENTS_SCHEMA

logger = logging.getLogger(__name__)

READER_STUDY_HELP_TEXTS = {
    "title": "The title of this reader study.",
    "logo": "The logo for this reader study.",
    "social_image": "An image for this reader study which is displayed when posting the reader study link on social media. Should have a resolution of 640x320 px (1280x640 px for best display).",
    "description": "Describe what this reader study is for.",
    "workstation": (
        "Which viewer should be used for this reader study? "
        "Note that in order to add a viewer you must be a member "
        "of that viewers users group. "
        "If you do not see the viewer that you want to use, "
        "please contact the admin for that viewer."
    ),
    "workstation_config": format_lazy(
        (
            "The viewer configuration to use for this reader study. "
            "If a suitable configuration does not exist you can "
            '<a href="{}">create a new one</a>. For a list of existing '
            'configurations, go <a href="{}">here</a>.'
        ),
        reverse_lazy("workstation-configs:create"),
        reverse_lazy("workstation-configs:list"),
    ),
    "help_text_markdown": (
        "Extra information that will be presented to the reader in the help "
        "text modal and on the reader study detail page."
    ),
    "publications": format_lazy(
        (
            "The publications associated with this reader study. "
            'If your publication is missing click <a href="{}">here</a> to add it '
            "and then refresh this page."
        ),
        reverse_lazy("publications:create"),
    ),
}


class ReaderStudyCreateForm(
    WorkstationUserFilterMixin, SaveFormInitMixin, ModelForm
):
    class Meta:
        model = ReaderStudy
        fields = (
            "title",
            "logo",
            "social_image",
            "description",
            "publications",
            "modalities",
            "structures",
            "organizations",
            "workstation",
            "workstation_config",
            "is_educational",
            "instant_verification",
            "public",
            "access_request_handling",
            "allow_answer_modification",
            "shuffle_hanging_list",
            "allow_case_navigation",
            "allow_show_all_annotations",
            "roll_over_answers_for_n_cases",
        )
        help_texts = READER_STUDY_HELP_TEXTS
        widgets = {
            "description": TextInput,
            "publications": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
            "organizations": Select2MultipleWidget,
        }
        labels = {
            "workstation": "Viewer",
            "workstation_config": "Viewer Configuration",
        }

    def clean(self):
        super().clean()

        if self.cleaned_data["roll_over_answers_for_n_cases"] > 0 and (
            self.cleaned_data["allow_case_navigation"]
            or self.cleaned_data["shuffle_hanging_list"]
        ):
            self.add_error(
                error=ValidationError(
                    "Rolling over answers should not be used together with case navigation or shuffling of the hanging list",
                    code="invalid",
                ),
                field=None,
            )

        if (
            self.cleaned_data["public"]
            and not self.cleaned_data["description"]
        ):
            self.add_error(
                error=ValidationError(
                    "Making a reader study public requires a description",
                    code="invalid",
                ),
                field=None,
            )

        if (
            self.cleaned_data["instant_verification"]
            and not self.cleaned_data["is_educational"]
        ):
            self.add_error(
                error=ValidationError(
                    "Reader study must be educational when instant verification is enabled."
                ),
                field="is_educational",
            )


class ReaderStudyUpdateForm(ReaderStudyCreateForm, ModelForm):
    class Meta(ReaderStudyCreateForm.Meta):
        fields = (
            "title",
            "logo",
            "social_image",
            "description",
            "publications",
            "modalities",
            "structures",
            "organizations",
            "workstation",
            "workstation_config",
            "hanging_protocol",
            "optional_hanging_protocols",
            "view_content",
            "help_text_markdown",
            "shuffle_hanging_list",
            "is_educational",
            "instant_verification",
            "public",
            "access_request_handling",
            "allow_answer_modification",
            "allow_case_navigation",
            "allow_show_all_annotations",
            "roll_over_answers_for_n_cases",
            "case_text",
        )
        widgets = {
            "case_text": JSONEditorWidget(schema=CASE_TEXT_SCHEMA),
            "help_text_markdown": MarkdownEditorWidget,
            "description": TextInput,
            "publications": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
            "organizations": Select2MultipleWidget,
            "optional_hanging_protocols": Select2MultipleWidget,
            "view_content": JSONEditorWidget(schema=VIEW_CONTENT_SCHEMA),
        }
        help_texts = {
            **READER_STUDY_HELP_TEXTS,
            "shuffle_hanging_list": (
                "If true, the order of the display sets will be uniquely shuffled "
                "for each reader. If false, the display sets will be "
                "ordered by the Order field that you have set on each display set."
            ),
            "case_text": (
                "Free text that can be included for each case, where the key "
                "is the filename and the value is free text. You can use "
                "markdown formatting in the text. Not all images in the "
                "reader study are required. "
                'e.g., {"a73512ee-1.2.276.0.542432.3.1.3.3546325986342": "This is *image 1*"}'
            ),
            "hanging_protocol": format_lazy(
                (
                    "The hanging protocol to use for this reader study. "
                    "If a suitable protocol does not exist you can "
                    '<a href="{}">create a new one</a>. For a list of existing '
                    'hanging protocols, go <a href="{}">here</a>.'
                ),
                reverse_lazy("hanging-protocols:create"),
                reverse_lazy("hanging-protocols:list"),
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        interface_slugs = (
            self.instance.display_sets.exclude(values__isnull=True)
            .values_list("values__interface__slug", flat=True)
            .order_by()
            .distinct()
        )
        self.fields["view_content"].help_text += (
            " The following interfaces are used in your reader study: "
            f"{', '.join(interface_slugs)}."
        )


class ReaderStudyCopyForm(Form):
    title = CharField(required=True)
    description = CharField(required=False, widget=Textarea())
    copy_display_sets = BooleanField(required=False, initial=True)
    copy_hanging_protocol = BooleanField(required=False, initial=True)
    copy_view_content = BooleanField(required=False, initial=True)
    copy_case_text = BooleanField(required=False, initial=True)
    copy_questions = BooleanField(required=False, initial=True)
    copy_readers = BooleanField(required=False, initial=True)
    copy_editors = BooleanField(required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Copy"))


class QuestionForm(SaveFormInitMixin, DynamicFormMixin, ModelForm):
    def __init__(self, *args, reader_study, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name in self.instance.read_only_fields:
            self.fields[field_name].required = False
            self.fields[field_name].disabled = True

        self.fields["reader_study"].queryset = ReaderStudy.objects.filter(
            pk=reader_study.pk
        )
        self.fields["reader_study"].initial = reader_study
        self.fields["reader_study"].disabled = True
        self.fields["reader_study"].hidden = True

        self.fields["answer_type"].widget = Select(
            attrs={
                "hx-get": reverse_lazy(
                    "reader-studies:question-interfaces",
                    kwargs={"slug": reader_study.slug},
                ),
                "hx-target": "#id_interface",
            }
        )
        self.fields["answer_type"].choices = AnswerType.choices

        self.helper = FormHelper()
        self.helper.form_tag = True
        self.helper.layout = Layout(
            Div(
                Field("question_text"),
                Field("help_text"),
                Field("answer_type"),
                Field("widget"),
                HTML(
                    f"<div "
                    f"hx-get={reverse_lazy('reader-studies:question-widgets', kwargs={'slug': reader_study.slug})!r} "
                    f"hx-trigger='change from:#id_answer_type' "
                    f"hx-target='#id_widget' "
                    f"hx-include='[id=id_answer_type]'>"
                    f"</div>"
                ),
                Fieldset(
                    "Answer validation and widget options",
                    "answer_min_value",
                    "answer_max_value",
                    "answer_step_size",
                    "answer_min_length",
                    "answer_max_length",
                    "answer_match_pattern",
                    css_class="border rounded px-2 my-4",
                ),
                Fieldset(
                    "Add options",
                    Formset("options"),
                    css_class="options-formset",
                ),
                Field("required"),
                Field("empty_answer_confirmation"),
                Field("empty_answer_confirmation_label"),
                Field("image_port"),
                Field("default_annotation_color"),
                Field("direction"),
                Field("order"),
                Field("interface"),
                Field("overlay_segments"),
                Field("look_up_table"),
                HTML("<br>"),
                ButtonHolder(Submit("save", "Save")),
            )
        )

    def __get_answer_type(self):
        if not self.instance.is_fully_editable:
            # disabled form elements are not sent along with the form,
            # so retrieve the answer type from the instance
            return self.instance.answer_type
        else:
            return self["answer_type"].value()

    def interface_choices(self):
        answer_type = self.__get_answer_type()
        if answer_type is None:
            return ComponentInterface.objects.none()
        return ComponentInterface.objects.filter(
            kind__in=ANSWER_TYPE_TO_INTERFACE_KIND_MAP[answer_type]
        )

    def widget_choices(self):
        answer_type = self.__get_answer_type()
        choices = [*BLANK_CHOICE_DASH]

        if not answer_type:
            return choices

        if answer_type in AnswerType.get_widget_required_types():
            choices = []  # No blank choice

        try:
            choices += ANSWER_TYPE_TO_QUESTION_WIDGET_CHOICES[answer_type]
        except KeyError as error:
            raise RuntimeError(
                f"{answer_type} is not defined in ANSWER_TYPE_TO_QUESTION_WIDGET_CHOICES."
            ) from error
        return choices

    def initial_widget(self):
        return self.instance.widget

    def clean(self):
        answer_type = self.cleaned_data.get("answer_type")
        interface = self.cleaned_data.get("interface")
        overlay_segments = self.cleaned_data.get("overlay_segments")

        if overlay_segments and answer_type != AnswerType.MASK:
            self.add_error(
                error=ValidationError(
                    "Overlay segments should only be set for Mask answers"
                ),
                field=None,
            )

        if interface and overlay_segments != interface.overlay_segments:
            self.add_error(
                error=ValidationError(
                    f"Overlay segments do not match those of {interface.title}. "
                    f"Please use {json.dumps(interface.overlay_segments)}."
                ),
                field=None,
            )
        return super().clean()

    class Meta:
        model = Question
        fields = (
            "question_text",
            "help_text",
            "answer_type",
            "required",
            "empty_answer_confirmation",
            "empty_answer_confirmation_label",
            "image_port",
            "default_annotation_color",
            "direction",
            "order",
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
            "reader_study",
        )
        help_texts = {
            "question_text": (
                "The question that will be presented to the user, "
                "should be short. "
                "e.g. 'Is there pathology present in these images?'"
            ),
            "help_text": (
                "This can be used to provide extra information or "
                "clarification to the reader about this question."
            ),
            "answer_type": "The type of answer that the user will give.",
            "image_port": (
                "If the user will make a bounding box or measurement, "
                "on which image port should they do it? "
                "Note, "
                "that this will be the same image port for every hanging."
            ),
            "direction": (
                "The format of the question, "
                "vertical means that the question text "
                "goes above the answer box, "
                "horizontal means that the question text "
                "will be on the same row as the answer box."
            ),
            "order": (
                "Where should this question be in the form? "
                "Lower numbers put this question to the top."
            ),
            "required": (
                "If true, the user must provide an answer or at least one annotation for this question, "
                "otherwise the user can skip it."
            ),
        }
        widgets = {
            "question_text": TextInput,
            "answer_match_pattern": TextInput,
            "empty_answer_confirmation_label": TextInput,
            "overlay_segments": JSONEditorWidget(
                schema=OVERLAY_SEGMENTS_SCHEMA
            ),
            "default_annotation_color": ColorEditorWidget(format="hex"),
        }

    interface = DynamicField(
        ModelChoiceField,
        queryset=interface_choices,
        initial=None,
        required=False,
        help_text="Select component interface to use as a default answer for this "
        "question.",
    )

    widget = DynamicField(
        ChoiceField,
        initial=initial_widget,
        choices=widget_choices,
        required=False,
        help_text="Select the input method that will be presented to the user. "
        "Which widgets are available depends on the answer type selected.",
    )


class CategoricalOptionForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].label = False

    class Meta:
        model = CategoricalOption
        fields = ("title", "default")


CategoricalOptionFormSet = inlineformset_factory(
    Question,
    CategoricalOption,
    form=CategoricalOptionForm,
    fields=["title", "default"],
    extra=1,
    can_delete=True,
)


class ReadersForm(UserGroupForm):
    role = "reader"

    def add_or_remove_user(self, *, obj):
        super().add_or_remove_user(obj=obj)

        user = self.cleaned_data["user"]

        try:
            permission_request = ReaderStudyPermissionRequest.objects.get(
                user=user, reader_study=obj
            )
        except ObjectDoesNotExist:
            return

        if self.cleaned_data["action"] == self.REMOVE:
            permission_request.status = ReaderStudyPermissionRequest.REJECTED
        else:
            permission_request.status = ReaderStudyPermissionRequest.ACCEPTED

        permission_request.save()


class ReaderStudyPermissionRequestUpdateForm(PermissionRequestUpdateForm):
    class Meta(PermissionRequestUpdateForm.Meta):
        model = ReaderStudyPermissionRequest


class GroundTruthForm(SaveFormInitMixin, Form):
    ground_truth = FileField(
        required=True,
        help_text="A csv file with a headers row containing the header `images`"
        " and the question text for each of the questions in this study."
        " The subsequent rows should then be filled with the image file"
        " names (separated by semicolons) and the answer corresponding to"
        " the question text provided in the header.",
    )

    def __init__(self, *args, user, reader_study, **kwargs):
        super().__init__(*args, **kwargs)
        self._reader_study = reader_study
        self._user = user
        self._answers = []

    def clean_ground_truth(self):
        csv_file = self.cleaned_data.get("ground_truth")
        csv_file.seek(0)

        rdr = csv.DictReader(
            io.StringIO(csv_file.read().decode("utf-8")),
            quoting=csv.QUOTE_ALL,
            escapechar="\\",
            quotechar="'",
        )
        headers = rdr.fieldnames

        if sorted(
            filter(lambda x: not x.endswith("__explanation"), headers)
        ) != sorted(self._reader_study.ground_truth_file_headers):
            raise ValidationError(
                f"Fields provided do not match with reader study. Fields should "
                f"be: {','.join(self._reader_study.ground_truth_file_headers)}"
            )

        ground_truth = [x for x in rdr]

        self.create_answers(ground_truth=ground_truth)

        return ground_truth

    def create_answers(self, *, ground_truth):  # noqa: C901
        self._answers = []

        for gt in ground_truth:
            display_set = self._reader_study.display_sets.get(pk=gt["case"])

            for key in gt.keys():
                if key == "case" or key.endswith("__explanation"):
                    continue

                question = self._reader_study.questions.get(question_text=key)
                answer = json.loads(gt[key])

                if answer is None and question.required is False:
                    continue

                if question.answer_type == Question.AnswerType.CHOICE:
                    try:
                        option = question.options.get(title=answer)
                        answer = option.pk
                    except CategoricalOption.DoesNotExist:
                        raise ValidationError(
                            f"Option {answer!r} is not valid for question {question.question_text}"
                        )

                if question.answer_type == Question.AnswerType.MULTIPLE_CHOICE:
                    answer = list(
                        question.options.filter(title__in=answer).values_list(
                            "pk", flat=True
                        )
                    )

                try:
                    explanation = json.loads(gt.get(key + "__explanation", ""))
                except (json.JSONDecodeError, TypeError):
                    explanation = ""

                common_answer_kwargs = {
                    "display_set": display_set,
                    "question": question,
                    "is_ground_truth": True,
                }

                try:
                    answer_obj = Answer.objects.get(**common_answer_kwargs)
                except ObjectDoesNotExist:
                    answer_obj = Answer(**common_answer_kwargs)

                # Update the answer object
                answer_obj.creator = self._user
                answer_obj.answer = answer
                answer_obj.explanation = explanation

                answer_obj.validate(
                    creator=answer_obj.creator,
                    question=answer_obj.question,
                    answer=answer_obj.answer,
                    is_ground_truth=answer_obj.is_ground_truth,
                    display_set=answer_obj.display_set,
                )

                self._answers.append(answer_obj)

    def save_answers(self):
        for answer in self._answers:
            answer.save()


class DisplaySetCreateForm(MultipleCIVForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["order"] = IntegerField(
            initial=(
                self.instance.order
                if self.instance
                else self.base_obj.next_display_set_order
            )
        )


class DisplaySetUpdateForm(DisplaySetCreateForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.is_editable:
            for _, field in self.fields.items():
                field.disabled = True
