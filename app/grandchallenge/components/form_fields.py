from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelChoiceField, MultiValueField
from django.utils.functional import cached_property

from grandchallenge.cases.models import Image
from grandchallenge.cases.widgets import (
    FlexibleImageField,
    FlexibleImageWidget,
    ImageSearchWidget,
)
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.components.schemas import INTERFACE_VALUE_SCHEMA
from grandchallenge.components.widgets import (
    FileSearchWidget,
    FlexibleFileWidget,
)
from grandchallenge.core.guardian import get_objects_for_user
from grandchallenge.core.validators import JSONValidator
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.serving.models import (
    get_component_interface_values_for_user,
)
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


INTERFACE_FORM_FIELD_PREFIX = "__INTERFACE_FIELD__"


class InterfaceFormField(forms.Field):
    _possible_widgets = {
        UserUploadMultipleWidget,
        UserUploadSingleWidget,
        JSONEditorWidget,
        FlexibleImageWidget,
        ImageSearchWidget,
        FlexibleFileWidget,
        FileSearchWidget,
    }

    def __init__(self, *, instance=None, user=None, form_data=None, **kwargs):
        self.instance = instance
        self.user = user
        self.form_data = form_data
        super().__init__(**kwargs)

        self.kwargs = {
            "required": self.required,
            "disabled": self.disabled,
            "initial": self.get_initial_value(),
            "label": instance.title.title(),
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
        elif (
            isinstance(self.initial, ComponentInterfaceValue)
            and not self.initial.has_value
        ):
            return None
        else:
            return self.initial

    def get_image_field(self):
        current_value = None

        if self.initial:
            if isinstance(self.initial, ComponentInterfaceValue):
                current_value = self.initial.image
            elif Image.objects.filter(pk=self.initial).exists():
                current_value = Image.objects.get(pk=self.initial)
            elif UserUpload.objects.filter(pk=self.initial).exists():
                current_value = UserUpload.objects.get(pk=self.initial)
            else:
                raise RuntimeError(
                    f"Unknown type for initial value: {self.initial}"
                )

        self.kwargs["widget"] = FlexibleImageWidget(
            help_text=self.help_text,
            user=self.user,
            current_value=current_value,
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
        current_value = None

        if self.initial:
            if isinstance(self.initial, ComponentInterfaceValue):
                current_value = self.initial.file
            elif (
                isinstance(self.initial, int) or self.initial.isdigit()
            ) and ComponentInterfaceValue.objects.filter(
                pk=self.initial
            ).exists():
                current_value = ComponentInterfaceValue.objects.get(
                    pk=self.initial
                )
            elif UserUpload.objects.filter(pk=self.initial).exists():
                current_value = UserUpload.objects.get(pk=self.initial)
            else:
                raise RuntimeError(
                    f"Unknown type for initial value: {self.initial}"
                )

        self.kwargs["widget"] = FlexibleFileWidget(
            help_text=self.help_text,
            user=self.user,
            current_value=current_value,
            # also passing the CIV as current value here so that we can
            # show the image name to the user rather than its pk
        )
        upload_queryset = get_objects_for_user(
            self.user,
            "uploads.change_userupload",
        ).filter(status=UserUpload.StatusChoices.COMPLETED)
        return FlexibleFileField(
            upload_queryset=upload_queryset,
            file_search_queryset=self.civs_for_user_for_interface,
            **self.kwargs,
        )

    @cached_property
    def civs_for_user_for_interface(self):
        return get_component_interface_values_for_user(
            user=self.user, interface=self.instance
        )

    @property
    def field(self):
        return self._field


class FlexibleFileField(MultiValueField):

    widget = FlexibleFileWidget

    def __init__(
        self,
        *args,
        file_search_queryset=None,
        upload_queryset=None,
        disabled=False,
        **kwargs,
    ):
        fields = [
            ModelChoiceField(queryset=file_search_queryset, required=False),
            ModelChoiceField(queryset=upload_queryset, required=False),
        ]
        super().__init__(
            *args,
            fields=fields,
            require_all_fields=False,
            **kwargs,
        )
        if disabled:
            self.widget.disabled = True

    def compress(self, values):
        if values:
            non_empty_values = [
                val for val in values if val and val not in self.empty_values
            ]
            if len(non_empty_values) != 1:
                raise ValidationError("Too many values returned.")
            return non_empty_values[0]
