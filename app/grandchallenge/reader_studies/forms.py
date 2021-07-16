import csv
import io
import itertools

from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    ButtonHolder,
    Div,
    Field,
    Fieldset,
    HTML,
    Layout,
    Submit,
)
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.forms import (
    BooleanField,
    CharField,
    FileField,
    Form,
    ModelChoiceField,
    ModelForm,
    TextInput,
    Textarea,
)
from django.forms.models import inlineformset_factory
from django.utils.text import format_lazy
from django_select2.forms import Select2MultipleWidget

from grandchallenge.core.forms import (
    PermissionRequestUpdateForm,
    SaveFormInitMixin,
    WorkstationUserFilterMixin,
)
from grandchallenge.core.layout import Formset
from grandchallenge.core.widgets import JSONEditorWidget, MarkdownEditorWidget
from grandchallenge.groups.forms import UserGroupForm
from grandchallenge.reader_studies.models import (
    Answer,
    CASE_TEXT_SCHEMA,
    CategoricalOption,
    HANGING_LIST_SCHEMA,
    Question,
    ReaderStudy,
    ReaderStudyPermissionRequest,
)
from grandchallenge.subdomains.utils import reverse_lazy

READER_STUDY_HELP_TEXTS = {
    "title": "The title of this reader study.",
    "logo": "The logo for this reader study.",
    "social_image": "An image for this reader study which is displayed when posting the reader study link on social media. Should have a resolution of 640x320 px (1280x640 px for best display).",
    "description": "Describe what this reader study is for.",
    "workstation": (
        "Which workstation should be used for this reader study? "
        "Note that in order to add a workstation you must be a member "
        "of that workstations users group. "
        "If you do not see the workstation that you want to use, "
        "please contact the admin for that workstation."
    ),
    "workstation_config": format_lazy(
        (
            "The workstation configuration to use for this reader study. "
            "If a suitable configuration does not exist you can "
            '<a href="{}">create a new one</a>.'
        ),
        reverse_lazy("workstation-configs:create"),
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
            "public",
            "allow_answer_modification",
            "allow_case_navigation",
            "allow_show_all_annotations",
        )
        help_texts = READER_STUDY_HELP_TEXTS
        widgets = {
            "description": TextInput,
            "publications": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
            "organizations": Select2MultipleWidget,
        }

    def clean(self):
        super().clean()
        if (
            self.cleaned_data["allow_answer_modification"]
            and not self.cleaned_data["allow_case_navigation"]
        ):
            self.add_error(
                error="`allow_case_navigation` must be checked if `allow_answer_modification` is",
                field=None,
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
            "help_text_markdown",
            "shuffle_hanging_list",
            "is_educational",
            "public",
            "allow_answer_modification",
            "allow_case_navigation",
            "allow_show_all_annotations",
            "hanging_list",
            "case_text",
        )
        widgets = {
            "hanging_list": JSONEditorWidget(schema=HANGING_LIST_SCHEMA),
            "case_text": JSONEditorWidget(schema=CASE_TEXT_SCHEMA),
            "help_text_markdown": MarkdownEditorWidget,
            "description": TextInput,
            "publications": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
            "organizations": Select2MultipleWidget,
        }
        help_texts = {
            **READER_STUDY_HELP_TEXTS,
            "shuffle_hanging_list": (
                "If true, each reader will read the images in a unique "
                "order. The ordering for each user will be consistent over "
                "time. If false, the readers will all read the images in the "
                "order that you define in the hanging_list field."
            ),
            "hanging_list": (
                "A list of hangings. "
                "The hanging defines which image (the hanging value) "
                "should be assigned to which image port or overlay. "
                "Options are: main, secondary, tertiary, quaternary, "
                "quinary, senary, septenary, octonary, nonary, denary. "
                "For instance: "
                '[{"main":"im1.mhd","main-overlay":"im1-overlay.mhd"}]'
            ),
            "case_text": (
                "Free text that can be included for each case, where the key "
                "is the filename and the value is free text. You can use "
                "markdown formatting in the text. Not all images in the "
                "reader study are required. "
                'e.g., {"a73512ee-1.2.276.0.542432.3.1.3.3546325986342": "This is *image 1*"}'
            ),
        }


class ReaderStudyCopyForm(Form):
    title = CharField(required=True)
    description = CharField(required=False, widget=Textarea())
    copy_images = BooleanField(required=False, initial=True)
    copy_hanging_list = BooleanField(required=False, initial=True)
    copy_case_text = BooleanField(required=False, initial=True)
    copy_questions = BooleanField(required=False, initial=True)
    copy_readers = BooleanField(required=False, initial=True)
    copy_editors = BooleanField(required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Copy"))

    def clean(self, *args, **kwargs):
        if (
            self.cleaned_data["copy_hanging_list"]
            or self.cleaned_data["copy_case_text"]
        ) and not self.cleaned_data["copy_images"]:
            self.add_error(
                error="Hanging list and case text can only be copied if the images are copied as well",
                field=None,
            )


class QuestionForm(SaveFormInitMixin, ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = True
        self.helper.layout = Layout(
            Div(
                Field("question_text"),
                Field("help_text"),
                Field("answer_type"),
                Fieldset(
                    "Add options",
                    Formset("options"),
                    css_class="options-formset",
                ),
                Field("required"),
                Field("image_port"),
                Field("direction"),
                Field("order"),
                HTML("<br>"),
                ButtonHolder(Submit("save", "Save")),
            )
        )

    def full_clean(self):
        """Override of the form's full_clean method.

        Some fields are made readonly once the question has been answered.
        Because disabled fields do not get included in the post data, this
        causes issues with required fields. Therefore we populate them here.
        """
        data = self.data.copy()
        for field in self.instance.read_only_fields:
            data[field] = getattr(self.instance, field)
        self.data = data
        return super().full_clean()

    class Meta:
        model = Question
        fields = (
            "question_text",
            "help_text",
            "answer_type",
            "required",
            "image_port",
            "direction",
            "order",
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
                "If true, the user must answer this question, otherwise the "
                "user can skip it."
            ),
        }
        widgets = {"question_text": TextInput}


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


class AnswersRemoveForm(Form):
    user = ModelChoiceField(
        queryset=get_user_model().objects.all().order_by("username"),
        required=True,
    )

    def remove_answers(self, *, reader_study):
        user = self.cleaned_data["user"]
        Answer.objects.filter(
            question__reader_study=reader_study,
            creator=user,
            is_ground_truth=False,
        ).delete()


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
        " the question text provided in the header. For Boolean type answers,"
        " use `0` for False and `1` for True.",
    )

    def __init__(self, *args, reader_study, **kwargs):
        super().__init__(*args, **kwargs)
        self.reader_study = reader_study

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
        ) != sorted(
            ["images"]
            + list(
                self.reader_study.questions.values_list(
                    "question_text", flat=True
                )
            )
        ):
            raise ValidationError(
                f"Fields provided do not match with reader study. Fields should "
                f"be: {','.join(self.reader_study.ground_truth_file_headers)}"
            )

        values = [x for x in rdr]

        images = sorted([sorted(x["images"].split(";")) for x in values])
        if images != sorted(self.reader_study.image_groups):
            diff = self.reader_study.hanging_list_diff(
                provided=list(itertools.chain(*images))
            )
            raise ValidationError(
                f"Images provided do not match hanging protocol. The following "
                f"images appear in the file, but not in the hanging list: "
                f"{', '.join(diff['in_provided_list'])}. These images appear "
                f"in the hanging list, but not in the file: "
                f"{', '.join(diff['in_hanging_list'])}."
            )

        return values
