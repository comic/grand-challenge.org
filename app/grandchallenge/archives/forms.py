from crispy_forms.helper import FormHelper
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.forms import (
    Form,
    ModelChoiceField,
    ModelForm,
    ModelMultipleChoiceField,
    TextInput,
)
from django.utils.text import format_lazy
from django_select2.forms import Select2MultipleWidget
from guardian.shortcuts import get_objects_for_user

from grandchallenge.archives.models import Archive, ArchivePermissionRequest
from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import Image
from grandchallenge.components.form_fields import InterfaceFormField
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKind,
)
from grandchallenge.core.forms import (
    PermissionRequestUpdateForm,
    SaveFormInitMixin,
    WorkstationUserFilterMixin,
)
from grandchallenge.core.templatetags.bleach import clean
from grandchallenge.core.widgets import MarkdownEditorWidget
from grandchallenge.groups.forms import UserGroupForm
from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.subdomains.utils import reverse_lazy


class ArchiveForm(WorkstationUserFilterMixin, SaveFormInitMixin, ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["logo"].required = True
        self.fields["workstation"].required = True
        self.fields["algorithms"].queryset = (
            self.instance.algorithms.all()
            | get_objects_for_user(
                kwargs["user"],
                "algorithms.execute_algorithm",
                accept_global_perms=False,
            )
        ).distinct()

    class Meta:
        model = Archive
        fields = (
            "title",
            "description",
            "publications",
            "modalities",
            "structures",
            "organizations",
            "logo",
            "social_image",
            "workstation",
            "workstation_config",
            "algorithms",
            "public",
            "require_user_review",
            "detail_page_markdown",
        )
        widgets = {
            "description": TextInput,
            "detail_page_markdown": MarkdownEditorWidget,
            "algorithms": Select2MultipleWidget,
            "publications": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
            "organizations": Select2MultipleWidget,
        }
        help_texts = {
            "workstation_config": format_lazy(
                (
                    "The viewer configuration to use for this archive. "
                    "If a suitable configuration does not exist you can "
                    '<a href="{}">create a new one</a>.'
                ),
                reverse_lazy("workstation-configs:create"),
            ),
            "publications": format_lazy(
                (
                    "The publications associated with this archive. "
                    'If your publication is missing click <a href="{}">here</a> to add it '
                    "and then refresh this page."
                ),
                reverse_lazy("publications:create"),
            ),
        }
        labels = {
            "workstation": "Viewer",
            "workstation_config": "Viewer Configuration",
        }


class UploadersForm(UserGroupForm):
    role = "uploader"


class UsersForm(UserGroupForm):
    role = "user"

    def add_or_remove_user(self, *, obj):
        super().add_or_remove_user(obj=obj)

        user = self.cleaned_data["user"]

        try:
            permission_request = ArchivePermissionRequest.objects.get(
                user=user, archive=obj
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
        queryset=ReaderStudy.objects.none(), required=True,
    )
    images = ModelMultipleChoiceField(
        queryset=Image.objects.none(),
        required=True,
        widget=Select2MultipleWidget,
    )

    def __init__(self, *args, user, archive, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.archive = archive

        self.fields["reader_study"].queryset = get_objects_for_user(
            self.user,
            "reader_studies.change_readerstudy",
            accept_global_perms=False,
        ).order_by("title")

        self.fields["images"].queryset = Image.objects.filter(
            componentinterfacevalue__archive_items__archive=self.archive
        ).distinct()
        self.fields["images"].initial = self.fields["images"].queryset

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


class AddCasesForm(UploadRawImagesForm):
    interface = ModelChoiceField(
        queryset=ComponentInterface.objects.filter(
            kind__in=InterfaceKind.interface_type_image()
        )
    )

    def save(self, *args, **kwargs):
        self._linked_task.kwargs.update(
            {"interface_pk": self.cleaned_data["interface"].pk}
        )
        return super().save(*args, **kwargs)


class ArchiveItemForm(SaveFormInitMixin, Form):
    def __init__(
        self, *args, user=None, archive_item=None, interface=None, **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()

        if archive_item:
            values = archive_item.values.all()
        else:
            values = ComponentInterfaceValue.objects.none()

        initial = values.filter(interface=interface).first()

        if initial:
            initial = initial.value

        self.fields[interface.slug] = InterfaceFormField(
            kind=interface.kind,
            schema=interface.schema,
            initial=initial or interface.default_value,
            required=False,
            user=user,
            help_text=clean(interface.description)
            if interface.description
            else "",
        ).field
