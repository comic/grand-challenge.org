from dal import autocomplete
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.forms import (
    ChoiceField,
    Form,
    HiddenInput,
    ModelChoiceField,
    ModelForm,
    ModelMultipleChoiceField,
    TextInput,
)
from django_select2.forms import Select2MultipleWidget
from guardian.shortcuts import get_objects_for_user
from guardian.utils import get_anonymous_user

from grandchallenge.archives.models import Archive, ArchivePermissionRequest
from grandchallenge.cases.models import Image
from grandchallenge.core.forms import (
    PermissionRequestUpdateForm,
    SaveFormInitMixin,
    WorkstationUserFilterMixin,
)
from grandchallenge.core.widgets import MarkdownEditorWidget
from grandchallenge.reader_studies.models import ReaderStudy


class ArchiveForm(WorkstationUserFilterMixin, SaveFormInitMixin, ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["logo"].required = True
        self.fields["workstation"].required = True

    class Meta:
        model = Archive
        fields = (
            "title",
            "description",
            "logo",
            "workstation",
            "workstation_config",
            "public",
            "detail_page_markdown",
        )
        widgets = {
            "description": TextInput,
            "detail_page_markdown": MarkdownEditorWidget,
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
            url="archives:users-autocomplete",
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

    def add_or_remove_user(self, *, archive):
        if self.cleaned_data["action"] == self.ADD:
            getattr(archive, f"add_{self.role}")(self.cleaned_data["user"])
        elif self.cleaned_data["action"] == self.REMOVE:
            getattr(archive, f"remove_{self.role}")(self.cleaned_data["user"])


class EditorsForm(UserGroupForm):
    role = "editor"


class UploadersForm(UserGroupForm):
    role = "uploader"


class UsersForm(UserGroupForm):
    role = "user"

    def add_or_remove_user(self, *, archive):
        super().add_or_remove_user(archive=archive)

        user = self.cleaned_data["user"]

        try:
            permission_request = ArchivePermissionRequest.objects.get(
                user=user, archive=archive
            )
        except ObjectDoesNotExist:
            return

        if self.cleaned_data["action"] == self.REMOVE:
            permission_request.status = ArchivePermissionRequest.REJECTED
        else:
            permission_request.status = ArchivePermissionRequest.ACCEPTED

        permission_request.save()


class ArchivePermissionRequestUpdateForm(PermissionRequestUpdateForm):
    class Meta(PermissionRequestUpdateForm.Meta):
        model = ArchivePermissionRequest


class ArchiveCasesToReaderStudyForm(SaveFormInitMixin, Form):
    reader_study = ModelChoiceField(
        queryset=ReaderStudy.objects.all(), required=True,
    )
    images = ModelMultipleChoiceField(
        queryset=Image.objects.all(),
        required=True,
        widget=Select2MultipleWidget,
    )

    def __init__(self, *args, user, archive, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.archive = archive

        self.fields["reader_study"].queryset = get_objects_for_user(
            self.user,
            f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}",
            ReaderStudy,
        ).order_by("title")
        self.fields["images"].queryset = Image.objects.filter(
            archive=self.archive
        )
        self.fields["images"].initial = self.fields["images"].queryset

    def clean_reader_study(self):
        reader_study = self.cleaned_data["reader_study"]
        if not self.user.has_perm("change_readerstudy", reader_study):
            raise ValidationError(
                "You do not have permission to change this reader study"
            )
        return reader_study

    def clean_images(self):
        images = self.cleaned_data["images"]
        images = images.filter(archive=self.archive)
        return images

    def clean(self):
        cleaned_data = super().clean()

        cleaned_data["images"] = cleaned_data["images"].exclude(
            readerstudies__in=[cleaned_data["reader_study"]]
        )

        if len(cleaned_data["images"]) == 0:
            raise ValidationError(
                "All of the selected images already exist in that reader study"
            )

        return cleaned_data
