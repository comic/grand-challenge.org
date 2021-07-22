from django.forms import (
    BooleanField,
    CharField,
    FloatField,
    IntegerField,
    JSONField,
)

from grandchallenge.cases.forms import IMAGE_UPLOAD_HELP_TEXT
from grandchallenge.components.models import InterfaceKind
from grandchallenge.components.schemas import INTERFACE_VALUE_SCHEMA
from grandchallenge.core.validators import ExtensionValidator
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.jqfileupload.widgets import uploader
from grandchallenge.jqfileupload.widgets.uploader import UploadedAjaxFileList

file_upload_text = (
    "The total size of all files uploaded in a single session "
    "cannot exceed 10 GB.<br>"
    "The following file formats are supported: "
)


def _join_with_br(a, b):
    if a:
        return f"{a}<br>{b}"
    else:
        return b


class InterfaceFormField:
    def __init__(
        self,
        *,
        kind: InterfaceKind.InterfaceKindChoices,
        initial=None,
        user=None,
        required=None,
        help_text="",
    ):
        field_type = field_for_interface(kind)

        # bool can't be required
        required = (
            required
            if required is not None
            else (kind != InterfaceKind.InterfaceKindChoices.BOOL)
        )
        kwargs = {
            "required": required,
        }

        extra_help = ""

        if initial is not None:
            kwargs["initial"] = initial
        if kind in InterfaceKind.interface_type_annotation():
            kwargs["widget"] = JSONEditorWidget(
                schema=INTERFACE_VALUE_SCHEMA["definitions"][kind]
            )
        if kind in InterfaceKind.interface_type_file():
            kwargs["widget"] = uploader.AjaxUploadWidget(
                multifile=False, auto_commit=False
            )
            kwargs["validators"] = [
                ExtensionValidator(allowed_extensions=(f".{kind.lower()}",))
            ]
            extra_help = f"{file_upload_text} .{kind.lower()}"
        if kind in InterfaceKind.interface_type_image():
            kwargs["widget"] = uploader.AjaxUploadWidget(
                multifile=True, auto_commit=False
            )
            extra_help = IMAGE_UPLOAD_HELP_TEXT

        self._field = field_type(
            help_text=_join_with_br(help_text, extra_help), **kwargs
        )

        if user:
            self._field.widget.user = user

    @property
    def field(self):
        return self._field


def field_for_interface(i: InterfaceKind.InterfaceKindChoices):
    fields = {}
    for kind in InterfaceKind.interface_type_annotation():
        fields[kind] = JSONField
    for kind in (
        InterfaceKind.interface_type_image()
        + InterfaceKind.interface_type_file()
    ):
        fields[kind] = UploadedAjaxFileList
    fields.update(
        {
            InterfaceKind.InterfaceKindChoices.BOOL: BooleanField,
            InterfaceKind.InterfaceKindChoices.STRING: CharField,
            InterfaceKind.InterfaceKindChoices.INTEGER: IntegerField,
            InterfaceKind.InterfaceKindChoices.FLOAT: FloatField,
        }
    )
    return fields[i]
