from crispy_forms.helper import FormHelper
from django.core.exceptions import ObjectDoesNotExist
from django.forms import (
    BooleanField,
    CharField,
    FloatField,
    Form,
    IntegerField,
    JSONField,
    ModelForm,
    TextInput,
)
from django.utils.text import format_lazy
from django_select2.forms import Select2MultipleWidget

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    AlgorithmPermissionRequest,
    Job,
)
from grandchallenge.components.models import InterfaceKind
from grandchallenge.core.forms import (
    PermissionRequestUpdateForm,
    SaveFormInitMixin,
    WorkstationUserFilterMixin,
)
from grandchallenge.core.validators import ExtensionValidator
from grandchallenge.core.widgets import JSONEditorWidget, MarkdownEditorWidget
from grandchallenge.groups.forms import UserGroupForm
from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.jqfileupload.widgets.uploader import UploadedAjaxFileList
from grandchallenge.reader_studies.models import ANSWER_TYPE_SCHEMA
from grandchallenge.subdomains.utils import reverse_lazy

image_upload_text = (
    "The total size of all files uploaded in a single session "
    "cannot exceed 10 GB.<br>"
    "The following file formats are supported: "
    ".mha, .mhd, .raw, .zraw, .dcm, .nii, .nii.gz, "
    ".tiff, .png, .jpeg and .jpg.<br>"
    "The following file formats can be uploaded and will be converted to "
    "tif: Aperio(.svs), Hamamatsu(.vms, .vmu, .ndpi), Leica(.scn), MIRAX"
    "(.mrxs) and Ventana(.bif)."
)

file_upload_text = (
    "The total size of all files uploaded in a single session "
    "cannot exceed 10 GB.<br>"
    "The following file formats are supported: "
)


class InterfaceFormField:
    def __init__(
        self, kind: InterfaceKind.InterfaceKindChoices, initial=None, user=None
    ):
        field_type = field_for_interface(kind)

        # bool can't be required
        kwargs = {
            "required": (kind != InterfaceKind.InterfaceKindChoices.BOOL)
        }
        if initial:
            kwargs["initial"] = initial
        if kind in InterfaceKind.interface_type_annotation():
            kwargs["widget"] = JSONEditorWidget(
                schema=ANSWER_TYPE_SCHEMA["definitions"][kind]
            )
        if kind in InterfaceKind.interface_type_file():
            kwargs["widget"] = uploader.AjaxUploadWidget(
                multifile=False, auto_commit=False
            )
            kwargs["help_text"] = f"{file_upload_text} .{kind.lower()}"
            kwargs["validators"] = [
                ExtensionValidator(allowed_extensions=(f".{kind.lower()}",))
            ]
        if kind in InterfaceKind.interface_type_image():
            kwargs["widget"] = uploader.AjaxUploadWidget(
                multifile=True, auto_commit=False
            )
            kwargs["help_text"] = image_upload_text
        self._field = field_type(**kwargs)
        if user:
            self._field.widget.user = user

    @property
    def field(self):
        return self._field


def field_for_interface(i: InterfaceKind.InterfaceKindChoices):
    if i == InterfaceKind.InterfaceKindChoices.BOOL:
        return BooleanField
    if i == InterfaceKind.InterfaceKindChoices.STRING:
        return CharField
    if i == InterfaceKind.InterfaceKindChoices.INTEGER:
        return IntegerField
    if i == InterfaceKind.InterfaceKindChoices.FLOAT:
        return FloatField
    if i == InterfaceKind.InterfaceKindChoices.BOOL:
        return BooleanField
    if i == InterfaceKind.InterfaceKindChoices.BOOL:
        return BooleanField
    if i in InterfaceKind.interface_type_annotation():
        return JSONField
    if (
        i in InterfaceKind.interface_type_image()
        or i in InterfaceKind.interface_type_file()
    ):
        return UploadedAjaxFileList


class AlgorithmInputsForm(SaveFormInitMixin, Form):
    def __init__(self, *args, algorithm=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if algorithm is None:
            return
        self.helper = FormHelper()
        for inp in algorithm.inputs.all():
            self.fields[inp.slug] = InterfaceFormField(
                inp.kind, inp.default_value, user
            ).field


class AlgorithmForm(WorkstationUserFilterMixin, SaveFormInitMixin, ModelForm):
    class Meta:
        model = Algorithm
        fields = (
            "title",
            "description",
            "publications",
            "modalities",
            "structures",
            "organizations",
            "logo",
            "social_image",
            "public",
            "inputs",
            "workstation",
            "workstation_config",
            "credits_per_job",
            "detail_page_markdown",
            "job_create_page_markdown",
            "additional_terms_markdown",
            "result_template",
        )
        widgets = {
            "description": TextInput,
            "detail_page_markdown": MarkdownEditorWidget,
            "job_create_page_markdown": MarkdownEditorWidget,
            "additional_terms_markdown": MarkdownEditorWidget,
            "result_template": MarkdownEditorWidget,
            "publications": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
            "organizations": Select2MultipleWidget,
        }
        help_texts = {
            "workstation_config": format_lazy(
                (
                    "The workstation configuration to use for this algorithm. "
                    "If a suitable configuration does not exist you can "
                    '<a href="{}">create a new one</a>.'
                ),
                reverse_lazy("workstation-configs:create"),
            )
        }


class AlgorithmImageForm(ModelForm):
    chunked_upload = UploadedAjaxFileList(
        widget=uploader.AjaxUploadWidget(multifile=False),
        label="Algorithm Image",
        validators=[
            ExtensionValidator(allowed_extensions=(".tar", ".tar.gz"))
        ],
        help_text=(
            ".tar.gz archive of the container image produced from the command "
            "'docker save IMAGE | gzip -c > IMAGE.tar.gz'. See "
            "https://docs.docker.com/engine/reference/commandline/save/"
        ),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.fields["chunked_upload"].widget.user = user

    class Meta:
        model = AlgorithmImage
        fields = ("requires_gpu", "chunked_upload")


class AlgorithmImageUpdateForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = AlgorithmImage
        fields = ("requires_gpu",)


class UsersForm(UserGroupForm):
    role = "user"

    def add_or_remove_user(self, *, obj):
        super().add_or_remove_user(obj=obj)

        user = self.cleaned_data["user"]

        try:
            permission_request = AlgorithmPermissionRequest.objects.get(
                user=user, algorithm=obj
            )
        except ObjectDoesNotExist:
            return

        if self.cleaned_data["action"] == self.REMOVE:
            permission_request.status = AlgorithmPermissionRequest.REJECTED
        else:
            permission_request.status = AlgorithmPermissionRequest.ACCEPTED

        permission_request.save()


class ViewersForm(UserGroupForm):
    role = "viewer"


class JobForm(SaveFormInitMixin, ModelForm):
    class Meta:
        model = Job
        fields = ("comment", "public")


class AlgorithmPermissionRequestUpdateForm(PermissionRequestUpdateForm):
    class Meta(PermissionRequestUpdateForm.Meta):
        model = AlgorithmPermissionRequest
