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
from grandchallenge.components.models import InterfaceKindChoices
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


class AlgorithmInputsForm(SaveFormInitMixin, Form):
    FORM_FIELDS = {
        InterfaceKindChoices.BOOL: {
            "class": BooleanField,
            "kwargs": {"required": False},
        },
        InterfaceKindChoices.STRING: {
            "class": CharField,
            "kwargs": {"required": True},
        },
        InterfaceKindChoices.INTEGER: {
            "class": IntegerField,
            "kwargs": {"required": True},
        },
        InterfaceKindChoices.FLOAT: {
            "class": FloatField,
            "kwargs": {"required": True},
        },
    }

    ANNOTATION_FORM_FIELDS = (
        InterfaceKindChoices.TWO_D_BOUNDING_BOX,
        InterfaceKindChoices.MULTIPLE_TWO_D_BOUNDING_BOXES,
        InterfaceKindChoices.DISTANCE_MEASUREMENT,
        InterfaceKindChoices.MULTIPLE_DISTANCE_MEASUREMENTS,
        InterfaceKindChoices.POINT,
        InterfaceKindChoices.MULTIPLE_POINTS,
        InterfaceKindChoices.POLYGON,
        InterfaceKindChoices.MULTIPLE_POLYGONS,
    )

    FILE_FORM_FIELDS = {
        InterfaceKindChoices.HEAT_MAP: {
            "help_text": image_upload_text,
            "validators": [],
        },
        InterfaceKindChoices.IMAGE: {
            "help_text": image_upload_text,
            "validators": [],
        },
        InterfaceKindChoices.SEGMENTATION: {
            "help_text": image_upload_text,
            "validators": [],
        },
        InterfaceKindChoices.CSV: {
            "help_text": f"{file_upload_text} .csv",
            "validators": [ExtensionValidator(allowed_extensions=(".csv",))],
        },
        InterfaceKindChoices.JSON: {
            "help_text": f"{file_upload_text} .json",
            "validators": [ExtensionValidator(allowed_extensions=(".json",))],
        },
        InterfaceKindChoices.ZIP: {
            "help_text": f"{file_upload_text} .zip",
            "validators": [ExtensionValidator(allowed_extensions=(".zip",))],
        },
    }

    def get_form_field(self, kind, initial, user):
        if kind in self.ANNOTATION_FORM_FIELDS:
            field = {
                "class": JSONField,
                "kwargs": {
                    "required": True,
                    "widget": JSONEditorWidget(
                        schema=ANSWER_TYPE_SCHEMA["definitions"][kind]
                    ),
                    "initial": initial,
                },
            }
            return field["class"](**field["kwargs"])

        if kind in self.FILE_FORM_FIELDS:
            field = {
                "class": UploadedAjaxFileList,
                "kwargs": {
                    "required": True,
                    "widget": uploader.AjaxUploadWidget(
                        multifile=True, auto_commit=False
                    ),
                    "help_text": self.FILE_FORM_FIELDS[kind]["help_text"],
                    "validators": self.FILE_FORM_FIELDS[kind]["validators"],
                },
            }
            field = field["class"](**field["kwargs"])

            field.widget.user = user
            return field

        if kind in self.FORM_FIELDS:
            field = self.FORM_FIELDS[kind]
            field["kwargs"]["initial"] = initial
            return field["class"](**field["kwargs"])

    def __init__(self, *args, algorithm=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if algorithm is None:
            return
        self.helper = FormHelper()
        for inp in algorithm.inputs.all():
            self.fields[inp.slug] = self.get_form_field(
                inp.kind, inp.default_value, user
            )


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
