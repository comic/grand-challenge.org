from django import forms
from django.forms import ModelChoiceField

from grandchallenge.cases.widgets import (
    FlexibleImageField,
    FlexibleImageWidget,
)
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.components.schemas import INTERFACE_VALUE_SCHEMA
from grandchallenge.components.widgets import SelectUploadWidget
from grandchallenge.core.guardian import get_objects_for_user
from grandchallenge.core.validators import JSONValidator
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.subdomains.utils import reverse
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
        FlexibleImageWidget,
    }

    def __init__(
        self,
        *,
        instance=None,
        initial=None,
        user=None,
        required=None,
        disabled=False,
        help_text="",
        existing_civs=None,
        form_data=None,
    ):
        self.instance = instance
        self.initial = initial
        self.user = user
        self.required = required
        self.disabled = disabled
        self.help_text = help_text
        self.existing_civs = existing_civs
        self.form_data = form_data

        self.kwargs = {
            "required": required,
            "disabled": disabled,
            "initial": self.get_initial_value(),
        }

        if instance.is_image_kind:
            self._field = self.get_image_field()
        elif instance.requires_file:
            self._field = self.get_file_field()
        elif instance.is_json_kind:
            self._field = self.get_json_field()
        else:
            raise RuntimeError(f"Unknown interface kind: {instance}")

    def get_initial_value(self):
        if (
            isinstance(self.initial, ComponentInterfaceValue)
            and self.initial.has_value
        ):
            if self.instance.is_image_kind:
                return self.initial.image.pk
            elif self.instance.requires_file:
                return self.initial.pk
            else:
                return self.initial.value
        else:
            return self.initial

    def get_image_field(self):
        self.kwargs["widget"] = FlexibleImageWidget(
            help_text=self.help_text,
            user=self.user,
            current_value=self.initial,
            # also passing the CIV as current value here so that we can
            # show the image name to the user rather than its pk
        )
        upload_queryset = get_objects_for_user(
            self.user,
            "uploads.change_userupload",
        ).filter(status=UserUpload.StatusChoices.COMPLETED)
        image_queryset = get_objects_for_user(self.user, "cases.view_image")
        return FlexibleImageField(
            upload_queryset=upload_queryset,
            image_queryset=image_queryset,
            **self.kwargs,
        )

    def get_json_field(self):
        field_type = self.instance.default_field
        default_schema = {
            **INTERFACE_VALUE_SCHEMA,
            "anyOf": [{"$ref": f"#/definitions/{self.instance.kind}"}],
        }
        if field_type == forms.JSONField:
            self.kwargs["widget"] = JSONEditorWidget(schema=default_schema)
        self.kwargs["validators"] = [
            JSONValidator(schema=default_schema),
            JSONValidator(schema=self.instance.schema),
        ]
        extra_help = ""
        return field_type(
            help_text=_join_with_br(self.help_text, extra_help), **self.kwargs
        )

    def get_file_field(self):
        key = f"value_type_{self.instance.slug}"
        # on JobCreateForm interfaces are prepended with underscore
        alt_key = f"value_type__{self.instance.slug}"
        if key in self.form_data.keys():
            type = self.form_data[key]
        elif alt_key in self.form_data.keys():
            type = self.form_data[alt_key]
        elif self.existing_civs:
            type = "civ"
        else:
            type = "uuid"

        if type == "uuid":
            ext = (
                "json"
                if self.instance.is_json_kind
                else self.instance.kind.lower()
            )
            extra_help = f"{file_upload_text} .{ext}"
            return ModelChoiceField(
                queryset=get_objects_for_user(
                    self.user,
                    "uploads.change_userupload",
                ).filter(status=UserUpload.StatusChoices.COMPLETED),
                widget=UserUploadSingleWidget(
                    allowed_file_types=self.instance.file_mimetypes
                ),
                label=self.instance.slug.title(),
                help_text=_join_with_br(self.help_text, extra_help),
                **self.kwargs,
            )
        elif type == "civ":
            return ModelChoiceField(
                queryset=self.existing_civs,
                label=self.instance.slug.title(),
                widget=SelectUploadWidget(
                    attrs={
                        "upload_link": reverse(
                            "components:file-upload",
                            kwargs={"interface_slug": self.instance.slug},
                        )
                    }
                ),
                **self.kwargs,
            )

    @property
    def field(self):
        return self._field
