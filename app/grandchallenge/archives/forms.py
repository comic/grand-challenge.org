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

from grandchallenge.archives.models import (
    Archive,
    ArchiveItem,
    ArchivePermissionRequest,
)
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
from grandchallenge.hanging_protocols.forms import ViewContentMixin
from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.subdomains.utils import reverse_lazy


class ArchiveForm(
    WorkstationUserFilterMixin,
    SaveFormInitMixin,
    ModelForm,
    ViewContentMixin,
):
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
            "hanging_protocol",
            "view_content",
            "algorithms",
            "public",
            "access_request_handling",
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
        widgets.update(ViewContentMixin.Meta.widgets)
        help_texts = {
            "workstation_config": format_lazy(
                (
                    "The viewer configuration to use for this archive. "
                    "If a suitable configuration does not exist you can "
                    '<a href="{}">create a new one</a>. For a list of existing '
                    'configurations, go <a href="{}">here</a>.'
                ),
                reverse_lazy("workstation-configs:create"),
                reverse_lazy("workstation-configs:list"),
            ),
            "publications": format_lazy(
                (
                    "The publications associated with this archive. "
                    'If your publication is missing click <a href="{}">here</a> to add it '
                    "and then refresh this page."
                ),
                reverse_lazy("publications:create"),
            ),
            "hanging_protocol": format_lazy(
                (
                    "The hanging protocol to use for this archive. "
                    "If a suitable protocol does not exist you can "
                    '<a href="{}">create a new one</a>. For a list of existing '
                    'hanging protocols, go <a href="{}">here</a>.'
                ),
                reverse_lazy("hanging-protocols:create"),
                reverse_lazy("hanging-protocols:list"),
            ),
        }
        help_texts.update(ViewContentMixin.Meta.help_texts)
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


class ArchiveItemsToReaderStudyForm(SaveFormInitMixin, Form):
    reader_study = ModelChoiceField(
        queryset=ReaderStudy.objects.none(), required=True
    )
    items = ModelMultipleChoiceField(
        queryset=ArchiveItem.objects.none(),
        required=True,
        widget=Select2MultipleWidget,
    )

    def __init__(self, *args, user, archive, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.archive = archive

        self.fields["reader_study"].queryset = (
            get_objects_for_user(
                self.user,
                "reader_studies.change_readerstudy",
                accept_global_perms=False,
            )
            .filter(use_display_sets=True)
            .order_by("title")
        )

        self.fields["items"].queryset = self.archive.items.all()
        self.fields["items"].initial = self.fields["items"].queryset

    def clean(self):
        cleaned_data = super().clean()

        return cleaned_data


class ArchiveCasesToReaderStudyForm(SaveFormInitMixin, Form):
    reader_study = ModelChoiceField(
        queryset=ReaderStudy.objects.none(), required=True
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
        self.fields["reader_study"].queryset = (
            get_objects_for_user(
                self.user,
                "reader_studies.change_readerstudy",
                accept_global_perms=False,
            )
            .exclude(use_display_sets=True)
            .order_by("title")
        )

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
        ),
        help_text=format_lazy(
            (
                'See the <a href="{}">list of interfaces</a> for more '
                "information about each interface. "
                "Please contact support if your desired output is missing."
            ),
            reverse_lazy("algorithms:component-interface-list"),
        ),
    )

    def save(self, *args, **kwargs):
        self._linked_task.kwargs.update(
            {"interface_pk": self.cleaned_data["interface"].pk}
        )
        return super().save(*args, **kwargs)


class ArchiveItemForm(SaveFormInitMixin, Form):
    def __init__(
        self, *args, user=None, archive_item=None, interface=None, **kwargs
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
