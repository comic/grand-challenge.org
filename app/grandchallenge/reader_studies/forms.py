from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
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
from guardian.utils import get_anonymous_user

from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.reader_studies.models import (
    ReaderStudy,
    HANGING_LIST_SCHEMA,
    Question,
)


class SaveFormInitMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))


class ReaderStudyCreateForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = ReaderStudy
        fields = ("title", "logo", "description", "workstation")


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


class QuestionCreateForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = Question
        fields = ("question_text", "answer_type", "order")


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
        if self.cleaned_data["action"] == EditorsForm.ADD:
            getattr(reader_study, f"add_{self.role}")(
                self.cleaned_data["user"]
            )
        elif self.cleaned_data["action"] == EditorsForm.REMOVE:
            getattr(reader_study, f"remove_{self.role}")(
                self.cleaned_data["user"]
            )


class EditorsForm(UserGroupForm):
    role = "editor"


class ReadersForm(UserGroupForm):
    role = "reader"
