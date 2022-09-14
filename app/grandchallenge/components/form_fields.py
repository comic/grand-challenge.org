from django import forms

from grandchallenge.cases.forms import IMAGE_UPLOAD_HELP_TEXT
from grandchallenge.components.schemas import INTERFACE_VALUE_SCHEMA
from grandchallenge.core.shortcuts import get_objects_for_user
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
    _possible_widgets = {
        UserUploadMultipleWidget,
        UserUploadSingleWidget,
        JSONEditorWidget,
    }

    def __init__(
        self,
        *,
        instance=None,
        initial=None,
        user=None,
        required=None,
        help_text="",
    ):
        kwargs = {"required": required}

        if initial is not None:
            kwargs["initial"] = initial

        field_type = instance.default_field

        if instance.is_image_kind:
            kwargs["widget"] = UserUploadMultipleWidget()
            kwargs["queryset"] = get_objects_for_user(
                user, "uploads.change_userupload", accept_global_perms=False
            ).filter(status=UserUpload.StatusChoices.COMPLETED)
            extra_help = IMAGE_UPLOAD_HELP_TEXT
        elif instance.requires_file:
            kwargs["widget"] = UserUploadSingleWidget(
                allowed_file_types=instance.file_mimetypes
            )
            kwargs["queryset"] = get_objects_for_user(
                user, "uploads.change_userupload", accept_global_perms=False
            ).filter(status=UserUpload.StatusChoices.COMPLETED)
            ext = "json" if instance.is_json_kind else instance.kind.lower()
            extra_help = f"{file_upload_text} .{ext}"
        elif instance.is_json_kind:
            default_schema = {
                **INTERFACE_VALUE_SCHEMA,
                "anyOf": [{"$ref": f"#/definitions/{instance.kind}"}],
            }
            if field_type == forms.JSONField:
                kwargs["widget"] = JSONEditorWidget(schema=default_schema)
            kwargs["validators"] = [
                JSONValidator(schema=default_schema),
                JSONValidator(schema=instance.schema),
            ]
            extra_help = ""
        else:
            raise RuntimeError(f"Unknown widget for {instance}")

        self._field = field_type(
            help_text=_join_with_br(help_text, extra_help), **kwargs
        )

    @property
    def field(self):
        return self._field
