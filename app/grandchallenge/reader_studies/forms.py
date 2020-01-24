import csv
import io

from dal import autocomplete
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import (
    ChoiceField,
    FileField,
    Form,
    HiddenInput,
    ModelChoiceField,
    ModelForm,
    TextInput,
)
from guardian.shortcuts import get_objects_for_user
from guardian.utils import get_anonymous_user

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.reader_studies.models import (
    HANGING_LIST_SCHEMA,
    Question,
    ReaderStudy,
)
from grandchallenge.workstations.models import Workstation

READER_STUDY_HELP_TEXTS = {
    "title": "The title of this reader study",
    "logo": "The logo for this reader study",
    "description": "Describe what this reader study is for",
    "workstation": (
        "Which workstation should be used for this reader study? "
        "Note that in order to add a workstation you must be a member "
        "of that workstations users group. "
        "If you do not see the workstation that you want to use, "
        "please contact the admin for that workstation."
    ),
}


class ReaderStudyCreateForm(SaveFormInitMixin, ModelForm):
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["workstation"].queryset = get_objects_for_user(
            user,
            f"{Workstation._meta.app_label}.view_{Workstation._meta.model_name}",
            Workstation,
        )

    class Meta:
        model = ReaderStudy
        fields = (
            "title",
            "logo",
            "description",
            "workstation",
            "workstation_config",
        )
        help_texts = READER_STUDY_HELP_TEXTS


class ReaderStudyUpdateForm(ReaderStudyCreateForm, ModelForm):
    class Meta(ReaderStudyCreateForm.Meta):
        fields = (
            "title",
            "logo",
            "description",
            "workstation",
            "workstation_config",
            "shuffle_hanging_list",
            "hanging_list",
        )
        widgets = {
            "hanging_list": JSONEditorWidget(schema=HANGING_LIST_SCHEMA)
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
                "should be assigned to which image port. "
                'e.g., [{"main":"im1.mhd","secondary":"im2.mhd"}]'
            ),
        }


class QuestionForm(SaveFormInitMixin, ModelForm):
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


class UserGroupForm(SaveFormInitMixin, Form):
    ADD = "ADD"
    REMOVE = "REMOVE"
    CHOICES = ((ADD, "Add"), (REMOVE, "Remove"))
    user = ModelChoiceField(
        queryset=get_user_model().objects.all().order_by("username"),
        help_text="Select a user that will be added to the group",
        required=True,
        widget=autocomplete.ModelSelect2(
            url="reader-studies:users-autocomplete",
            attrs={
                "data-placeholder": "Search for a user ...",
                "data-minimum-input-length": 3,
                "data-theme": settings.CRISPY_TEMPLATE_PACK,
            },
        ),
    )
    action = ChoiceField(
        choices=CHOICES, required=True, widget=HiddenInput(), initial=ADD
    )

    def clean_user(self):
        user = self.cleaned_data["user"]
        if user == get_anonymous_user():
            raise ValidationError("You cannot add this user!")
        return user

    def add_or_remove_user(self, *, reader_study):
        if self.cleaned_data["action"] == self.ADD:
            getattr(reader_study, f"add_{self.role}")(
                self.cleaned_data["user"]
            )
        elif self.cleaned_data["action"] == self.REMOVE:
            getattr(reader_study, f"remove_{self.role}")(
                self.cleaned_data["user"]
            )


class EditorsForm(UserGroupForm):
    role = "editor"


class ReadersForm(UserGroupForm):
    role = "reader"


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
        rdr = csv.DictReader(io.StringIO(csv_file.read().decode("utf-8")))
        headers = rdr.fieldnames
        if sorted(headers) != sorted(
            ["images"]
            + list(
                self.reader_study.questions.values_list(
                    "question_text", flat=True
                )
            )
        ):
            raise ValidationError(
                "Fields provided do not match with reader study"
            )

        values = [x for x in rdr]

        if sorted([sorted(x["images"].split(";")) for x in values]) != sorted(
            self.reader_study.image_groups
        ):
            raise ValidationError(
                "Images provided do not match hanging protocol"
            )

        return values
