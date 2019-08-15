from dal import autocomplete
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import (
    ModelForm,
    Form,
    ModelChoiceField,
    ChoiceField,
    HiddenInput,
)
from guardian.shortcuts import get_objects_for_user
from guardian.utils import get_anonymous_user

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.reader_studies.models import (
    ReaderStudy,
    HANGING_LIST_SCHEMA,
    Question,
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
        fields = ("title", "logo", "description", "workstation")
        help_texts = READER_STUDY_HELP_TEXTS


class ReaderStudyUpdateForm(ReaderStudyCreateForm, ModelForm):
    class Meta(ReaderStudyCreateForm.Meta):
        fields = (
            "title",
            "logo",
            "description",
            "workstation",
            "hanging_list",
        )
        widgets = {
            "hanging_list": JSONEditorWidget(schema=HANGING_LIST_SCHEMA)
        }
        help_texts = {
            **READER_STUDY_HELP_TEXTS,
            "hanging_list": (
                "A list of hangings. "
                "The hanging defines which image (the hanging value) "
                "should be assigned to which image port. "
                'e.g., [{"main":"im1.mhd","secondary":"im2.mhd"}]'
            ),
        }


class QuestionCreateForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = Question
        fields = (
            "question_text",
            "answer_type",
            "image_port",
            "direction",
            "order",
        )
        help_texts = {
            "question_text": (
                "The question that will be presented to the user. "
                "e.g. 'Is there pathology present in these images?'"
            ),
            "answer_type": "The type of answer that the user will give.",
            "image_port": (
                "If the user is expected to draw a bounding box, "
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
        }


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
