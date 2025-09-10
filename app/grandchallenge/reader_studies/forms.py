import csv
import io
import json
import logging

from crispy_forms.bootstrap import FormActions
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
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import BLANK_CHOICE_DASH
from django.db.transaction import on_commit
from django.forms import (
    BooleanField,
    CharField,
    ChoiceField,
    FileField,
    Form,
    HiddenInput,
    IntegerField,
    ModelChoiceField,
    ModelForm,
    Select,
    Textarea,
    TextInput,
)
from django.forms.models import inlineformset_factory
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.text import format_lazy
from django_select2.forms import Select2MultipleWidget, Select2Widget
from dynamic_forms import DynamicField, DynamicFormMixin

from grandchallenge.components.forms import (
    CIVSetCreateFormMixin,
    CIVSetUpdateFormMixin,
    MultipleCIVForm,
)
from grandchallenge.components.models import ComponentInterface
from grandchallenge.core.forms import (
    PermissionRequestUpdateForm,
    SaveFormInitMixin,
    UniqueTitleCreateFormMixin,
    UniqueTitleUpdateFormMixin,
    WorkstationUserFilterMixin,
)
from grandchallenge.core.layout import Formset
from grandchallenge.core.widgets import (
    ColorEditorWidget,
    JSONEditorWidget,
    MarkdownEditorInlineWidget,
)
from grandchallenge.groups.forms import UserGroupForm
from grandchallenge.hanging_protocols.forms import ViewContentExampleMixin
from grandchallenge.hanging_protocols.models import VIEW_CONTENT_SCHEMA
from grandchallenge.reader_studies.models import (
    ANSWER_TYPE_TO_INTERACTIVE_ALGORITHM_CHOICES,
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
from grandchallenge.reader_studies.tasks import (
    answers_from_ground_truth,
    bulk_assign_scores_for_reader_study,
)
from grandchallenge.subdomains.utils import reverse, reverse_lazy
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
            "leaderboard_accessible_to_readers",
            "instant_verification",
            "public",
            "access_request_handling",
            "allow_answer_modification",
            "shuffle_hanging_list",
            "allow_case_navigation",
            "enable_autosaving",
            "allow_show_all_annotations",
            "roll_over_answers_for_n_cases",
            "end_of_study_text_markdown",
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
        cleaned_data = super().clean()

        if cleaned_data["roll_over_answers_for_n_cases"] > 0 and (
            cleaned_data["allow_case_navigation"]
            or cleaned_data["shuffle_hanging_list"]
        ):
            self.add_error(
                error=ValidationError(
                    "Rolling over answers should not be used together with case navigation or shuffling of the hanging list",
                    code="invalid",
                ),
                field=None,
            )

        if cleaned_data["public"] and not cleaned_data["description"]:
            self.add_error(
                error=ValidationError(
                    "Making a reader study public requires a description",
                    code="invalid",
                ),
                field=None,
            )

        if (
            cleaned_data["instant_verification"]
            and not cleaned_data["is_educational"]
        ):
            self.add_error(
                error=ValidationError(
                    "Reader study must be educational when instant verification is enabled."
                ),
                field="is_educational",
            )

        if (
            cleaned_data["leaderboard_accessible_to_readers"]
            and not cleaned_data["is_educational"]
        ):
            self.add_error(
                error=ValidationError(
                    "Reader study must be educational when making leaderboard accessible to readers."
                ),
                field="is_educational",
            )

        if (
            cleaned_data["enable_autosaving"]
            and not cleaned_data["allow_answer_modification"]
        ):
            self.add_error(
                error=ValidationError(
                    "Autosaving can only be enabled when also allowing answer modification."
                ),
                field="enable_autosaving",
            )

        return cleaned_data


class ReaderStudyUpdateForm(
    ReaderStudyCreateForm, ViewContentExampleMixin, ModelForm
):
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
            "leaderboard_accessible_to_readers",
            "instant_verification",
            "public",
            "access_request_handling",
            "allow_answer_modification",
            "enable_autosaving",
            "allow_case_navigation",
            "allow_show_all_annotations",
            "roll_over_answers_for_n_cases",
            "case_text",
            "end_of_study_text_markdown",
        )
        widgets = {
            "case_text": JSONEditorWidget(schema=CASE_TEXT_SCHEMA),
            "help_text_markdown": MarkdownEditorInlineWidget,
            "description": TextInput,
            "publications": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
            "organizations": Select2MultipleWidget,
            "optional_hanging_protocols": Select2MultipleWidget,
            "view_content": JSONEditorWidget(schema=VIEW_CONTENT_SCHEMA),
            "end_of_study_text_markdown": MarkdownEditorInlineWidget,
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


class ReaderStudyCopyForm(Form):
    title = CharField(required=True)
    description = CharField(required=False, widget=Textarea())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name in ReaderStudy.optional_copy_fields:
            self.fields[f"copy_{field_name}"] = BooleanField(
                required=False, initial=True
            )

        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Copy"))


class QuestionForm(SaveFormInitMixin, DynamicFormMixin, ModelForm):
    def __init__(self, *args, user, reader_study, **kwargs):
        self._user = user

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
        self.fields["answer_type"].choices = [
            *BLANK_CHOICE_DASH,
            *AnswerType.choices,
        ]

        self.fields["overlay_segments"].help_text += format_lazy(
            'Refer to the <a href="{}#segmentation-masks">documentation</a> for more information',
            reverse(
                "documentation:detail",
                kwargs={"slug": settings.DOCUMENTATION_HELP_INTERFACES_SLUG},
            ),
        )

        if not self.user_can_add_interactive_algorithm:
            self.fields["interactive_algorithm"].widget = HiddenInput()
            self.fields["interactive_algorithm"].disabled = True

        options_form_set_factory = inlineformset_factory(
            Question,
            CategoricalOption,
            form=CategoricalOptionForm,
            fields=["title", "default"],
            extra=(
                0
                if Question.objects.filter(pk=self.instance.pk).exists()
                else 1
            ),
            can_delete=self.instance.is_fully_editable,
        )

        self.options_form_set = options_form_set_factory(
            instance=self.instance,
            data=kwargs.get("data"),
            form_kwargs={"is_editable": self.instance.is_fully_editable},
        )

        self.helper = FormHelper()
        self.helper.form_tag = True
        self.helper.layout = Layout(
            Div(
                Field("question_text"),
                Field("help_text"),
                Field("answer_type"),
                Field("widget"),
                HTML(
                    format_html(
                        "<div hx-get={link} "
                        "hx-trigger='change from:#id_answer_type' "
                        "hx-target='#id_widget' "
                        "hx-include='[id=id_answer_type]'>"
                        "</div>",
                        link=reverse_lazy(
                            "reader-studies:question-widgets",
                            kwargs={"slug": reader_study.slug},
                        ),
                    )
                ),
                HTML(
                    format_html(
                        "<div hx-get={link} "
                        "hx-trigger='change from:#id_answer_type' "
                        "hx-target='#id_interactive_algorithm' "
                        "hx-include='[id=id_answer_type]'></div>",
                        link=reverse_lazy(
                            "reader-studies:question-interactive-algorithms",
                            kwargs={"slug": reader_study.slug},
                        ),
                    )
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
                    Formset(
                        formset=self.options_form_set,
                        can_add_another=self.instance.is_fully_editable,
                    ),
                    css_class="options-formset border rounded px-2 my-4",
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
                Field("interactive_algorithm"),
                HTML("<br>"),
                ButtonHolder(Submit("save", "Save")),
            )
        )

    @cached_property
    def user_can_add_interactive_algorithm(self):
        return self._user.has_perm(
            "reader_studies.add_interactive_algorithm_to_question"
        )

    @property
    def answer_type(self):
        if not self.instance.is_fully_editable:
            # disabled form elements are not sent along with the form,
            # so retrieve the answer type from the instance
            return self.instance.answer_type
        else:
            return self["answer_type"].value()

    def interface_choices(self):
        if self.answer_type is None:
            return ComponentInterface.objects.none()
        return ComponentInterface.objects.filter(
            kind__in=ANSWER_TYPE_TO_INTERFACE_KIND_MAP.get(
                self.answer_type, []
            )
        )

    def widget_choices(self):
        choices = [*BLANK_CHOICE_DASH]

        if not self.answer_type:
            return choices

        if self.answer_type in AnswerType.get_widget_required_types():
            choices = []  # No blank choice

        try:
            choices += ANSWER_TYPE_TO_QUESTION_WIDGET_CHOICES[self.answer_type]
        except KeyError as error:
            raise RuntimeError(
                f"{self.answer_type} is not defined in ANSWER_TYPE_TO_QUESTION_WIDGET_CHOICES."
            ) from error
        return choices

    def interactive_algorithm_choices(self):
        choices = [*BLANK_CHOICE_DASH]

        if not self.user_can_add_interactive_algorithm:
            return choices

        if not self.answer_type:
            return choices

        try:
            choices += ANSWER_TYPE_TO_INTERACTIVE_ALGORITHM_CHOICES[
                self.answer_type
            ]
        except KeyError as error:
            raise RuntimeError(
                f"{self.answer_type} is not defined in ANSWER_TYPE_TO_QUESTION_WIDGET_CHOICES."
            ) from error

        return choices

    def initial_widget(self):
        return self.instance.widget

    def initial_interactive_algorithm(self):
        return self.instance.interactive_algorithm

    def is_valid(self):
        return super().is_valid() and self.options_form_set.is_valid()

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

        self.options_form_set.clean()

        if self.options_form_set.is_valid():
            # The user will first need to make each instance valid,
            # then we can check the set of options

            new_forms = [
                form
                for form in self.options_form_set.extra_forms
                if form.has_changed()
                and not self.options_form_set._should_delete_form(form)
            ]
            existing_forms = [
                form
                for form in self.options_form_set.initial_forms
                if form.instance.pk is not None
                and form not in self.options_form_set.deleted_forms
            ]

            final_forms = new_forms + existing_forms

            if (
                len(final_forms) < 1
                and answer_type in Question.AnswerType.get_choice_types()
            ):
                self.add_error(
                    error=ValidationError(
                        "At least one option should be supplied for (multiple) choice questions"
                    ),
                    field=None,
                )

            if sum(form.cleaned_data["default"] for form in final_forms) > 1:
                self.add_error(
                    error=ValidationError(
                        "Only one option can be set as default"
                    ),
                    field=None,
                )

        return super().clean()

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        self.options_form_set.save(*args, **kwargs)
        return instance

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
            "interactive_algorithm",
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
        label="Socket",
        queryset=interface_choices,
        initial=None,
        required=False,
        help_text="Select socket to use as a default answer for this "
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

    interactive_algorithm = DynamicField(
        ChoiceField,
        initial=initial_interactive_algorithm,
        choices=interactive_algorithm_choices,
        required=False,
        help_text="Select an interactive algorithm for this question. Please note that setting an interactive algorithm will increase the credit consumption rate.",
    )


class CategoricalOptionForm(ModelForm):
    def __init__(self, *args, is_editable, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["title"].label = False
        self.fields["title"].required = True

        if not is_editable:
            for field_name in self.fields:
                self.fields[field_name].disabled = True

        self.helper = FormHelper()
        self.helper.form_tag = False

    class Meta:
        model = CategoricalOption
        fields = ("title", "default")


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


class GroundTruthFromAnswersForm(SaveFormInitMixin, Form):
    user = ModelChoiceField(
        queryset=get_user_model().objects.none(),
        required=True,
        help_text=format_html(
            "Select a user whose answers will be consumed. "
            "Only users that have <strong>completed the reader study</strong> are valid options."
        ),
        widget=Select2Widget,
    )

    def __init__(self, *args, reader_study, **kwargs):
        super().__init__(*args, **kwargs)

        self._reader_study = reader_study

        self.fields["user"].queryset = (
            get_user_model()
            .objects.filter(answer__question__reader_study=reader_study)
            .distinct()
        )

    def clean(self):
        if self._reader_study.has_ground_truth:
            raise ValidationError(
                "Reader study already has ground truth. Ground truth cannot be updated. "
                "Please, first delete the ground truth."
            )
        return super().clean()

    def clean_user(self):
        user = self.cleaned_data["user"]

        progress = self._reader_study.get_progress_for_user(user)
        if progress["questions"] != 100.0:
            raise ValidationError("User has not completed the reader study!")

        return user

    def create_ground_truth(self):
        answers = Answer.objects.filter(
            question__in=self._reader_study.ground_truth_applicable_questions,
            creator=self.cleaned_data["user"],
        )
        answers.update(is_ground_truth=True)

        # Unassign all scores: some are invalid now
        Answer.objects.filter(
            question__reader_study=self._reader_study
        ).update(score=None)

        on_commit(
            bulk_assign_scores_for_reader_study.signature(
                kwargs={"reader_study_pk": self._reader_study.pk}
            ).apply_async
        )


class AnswersFromGroundTruthForm(SaveFormInitMixin, Form):
    def __init__(self, *args, reader_study, request_user, **kwargs):
        super().__init__(*args, **kwargs)

        self._reader_study = reader_study
        self._user = request_user

        self.helper = FormHelper()
        self.helper.layout = Layout(
            FormActions(
                HTML(
                    format_html(
                        '<a class="btn btn-secondary" href="{ground_truth_url}">Cancel</a>',
                        ground_truth_url=reverse(
                            "reader-studies:ground-truth",
                            kwargs={"slug": reader_study.slug},
                        ),
                    )
                ),
                Submit(
                    "submit",
                    "Yes, create Answers for Me",
                    css_class="btn btn-primary",
                ),
            )
        )

    def clean(self):
        if Answer.objects.filter(
            question__reader_study=self._reader_study,
            creator=self._user,
            is_ground_truth=False,
        ).exists():
            raise ValidationError(
                "User already has answers. Delete these first"
            )

        return super().clean()

    def schedule_answers_from_ground_truth_task(self):
        on_commit(
            answers_from_ground_truth.signature(
                kwargs={
                    "reader_study_pk": self._reader_study.pk,
                    "target_user_pk": self._user.pk,
                }
            ).apply_async
        )


class GroundTruthCSVForm(SaveFormInitMixin, Form):
    ground_truth = FileField(
        required=True,
        help_text="A CSV file representing the ground truth.",
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
        Answer.objects.filter(
            question__reader_study=self._reader_study
        ).update(score=None)

        for answer in self._answers:
            answer.save()

        on_commit(
            bulk_assign_scores_for_reader_study.signature(
                kwargs={"reader_study_pk": self._reader_study.pk}
            ).apply_async
        )


class DisplaySetFormMixin(Form):
    class Meta:
        non_interface_fields = (
            "title",
            "order",
        )

    @property
    def model(self):
        return self.base_obj.civ_set_model

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        field_order = list(self.field_order or self.fields.keys())
        self.fields["order"] = IntegerField(
            initial=(
                self.instance.order
                if self.instance
                else self.base_obj.next_display_set_order
            ),
            min_value=0,
        )
        self.order_fields(["order", *field_order])

    def unique_title_query(self, *args, **kwargs):
        return (
            super()
            .unique_title_query(*args, **kwargs)
            .filter(reader_study=self.base_obj)
        )

    def clean(self):
        cleaned_data = super().clean()
        for field in self.model._meta.fields:
            if value := cleaned_data.get(field.name, None):
                cleaned_data[field.name] = field.clean(value, self.model)
        return cleaned_data


class DisplaySetCreateForm(
    DisplaySetFormMixin,
    UniqueTitleCreateFormMixin,
    CIVSetCreateFormMixin,
    MultipleCIVForm,
):
    pass


class DisplaySetUpdateForm(
    DisplaySetFormMixin,
    UniqueTitleUpdateFormMixin,
    CIVSetUpdateFormMixin,
    MultipleCIVForm,
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.is_editable:
            for _, field in self.fields.items():
                field.disabled = True
