from typing import Dict

from django import forms
from guardian.shortcuts import get_objects_for_user

from grandchallenge.cases.forms import IMAGE_UPLOAD_HELP_TEXT
from grandchallenge.components.models import InterfaceKind
from grandchallenge.components.schemas import INTERFACE_VALUE_SCHEMA
from grandchallenge.core.validators import JSONValidator
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import (
    UserUploadMultipleWidget,
    UserUploadSingleWidget,
)

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
        schema: Dict,
        initial=None,
        user=None,
        required=None,
        help_text="",
    ):
        field_type = InterfaceKind.get_default_field(kind=kind)
        kwargs = {"required": required}

        if initial is not None:
            kwargs["initial"] = initial

        if kind in InterfaceKind.interface_type_image():
            kwargs["widget"] = UserUploadMultipleWidget()
            kwargs["queryset"] = get_objects_for_user(
                user, "uploads.change_userupload", accept_global_perms=False
            ).filter(status=UserUpload.StatusChoices.COMPLETED)
            extra_help = IMAGE_UPLOAD_HELP_TEXT
        elif kind in InterfaceKind.interface_type_file():
            kwargs["widget"] = UserUploadSingleWidget(
                allowed_file_types=InterfaceKind.get_file_mimetypes(kind=kind)
            )
            kwargs["queryset"] = get_objects_for_user(
                user, "uploads.change_userupload", accept_global_perms=False
            ).filter(status=UserUpload.StatusChoices.COMPLETED)
            extra_help = f"{file_upload_text} .{kind.lower()}"
        elif kind in InterfaceKind.interface_type_json():
            default_schema = {
                **INTERFACE_VALUE_SCHEMA,
                "anyOf": [{"$ref": f"#/definitions/{kind}"}],
            }
            if field_type == forms.JSONField:
                kwargs["widget"] = JSONEditorWidget(schema=default_schema)
            kwargs["validators"] = [
                JSONValidator(schema=default_schema),
                JSONValidator(schema=schema),
            ]
            extra_help = ""
        else:
            raise RuntimeError(f"Unknown kind {kind}")

        self._field = field_type(
            help_text=_join_with_br(help_text, extra_help), **kwargs
        )

    @property
    def field(self):
        return self._field
