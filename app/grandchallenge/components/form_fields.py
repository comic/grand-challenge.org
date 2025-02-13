from django import forms
from django.core.exceptions import ValidationError
from django.db.models import TextChoices
from django.forms import ModelChoiceField, MultiValueField

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


class InterfaceFormFieldFactory:
    possible_widgets = {
        UserUploadMultipleWidget,
        UserUploadSingleWidget,
        JSONEditorWidget,
        FlexibleImageWidget,
        ImageSearchWidget,
        FlexibleFileWidget,
        FileSearchWidget,
    }

    def __init__(
        self,
        *,
        interface=None,
        user=None,
        required=True,
        initial=None,
        help_text="",
        disabled=False,
    ):
        if (
            isinstance(initial, ComponentInterfaceValue)
            and not initial.has_value
        ):
            initial = None
        self.interface = interface
        self.user = user
        self.initial = initial
        self.help_text = help_text

        self.kwargs = {
            "required": required,
            "disabled": disabled,
            "label": interface.title.title(),
        }

        if interface.is_image_kind:
            self._field = self.get_image_field()
        elif interface.requires_file:
            self._field = self.get_file_field()
        elif interface.is_json_kind:
            self._field = self.get_json_field()
        else:
            raise RuntimeError(f"Unknown interface kind: {interface}")

    def get_image_field(self):
        upload_queryset = get_objects_for_user(
            self.user,
            "uploads.change_userupload",
        ).filter(status=UserUpload.StatusChoices.COMPLETED)
        image_queryset = get_objects_for_user(self.user, "cases.view_image")
        return FlexibleImageField(
            user=self.user,
            initial=self.initial,
            upload_queryset=upload_queryset,
            image_queryset=image_queryset,
            help_text=self.help_text,
            **self.kwargs,
        )

    def get_json_field(self):
        if isinstance(self.initial, ComponentInterfaceValue):
            self.initial = self.initial.value
        self.kwargs["initial"] = self.initial
        field_type = self.interface.default_field
        default_schema = {
            **INTERFACE_VALUE_SCHEMA,
            "anyOf": [{"$ref": f"#/definitions/{self.interface.kind}"}],
        }
        if field_type == forms.JSONField:
            self.kwargs["widget"] = JSONEditorWidget(schema=default_schema)
        self.kwargs["validators"] = [
            JSONValidator(schema=default_schema),
            JSONValidator(schema=self.interface.schema),
        ]
        extra_help = ""
        return field_type(
            help_text=_join_with_br(self.help_text, extra_help), **self.kwargs
        )

    def get_file_field(self):
        return FlexibleFileField(
            user=self.user,
            interface=self.interface,
            initial=self.initial,
            help_text=self.help_text,
            **self.kwargs,
        )

    @property
    def field(self):
        return self._field


class FileWidgetChoices(TextChoices):
    FILE_SEARCH = "FILE_SEARCH"
    FILE_UPLOAD = "FILE_UPLOAD"
    FILE_SELECTED = "FILE_SELECTED"
    UNDEFINED = "UNDEFINED"


class FlexibleFileField(MultiValueField):

    widget = FlexibleFileWidget

    def __init__(
        self,
        *args,
        user=None,
        interface=None,
        initial=None,
        **kwargs,
    ):
        self.user = user
        self.interface = interface

        # The `current_value` is added to the widget attrs to display in the initial dropdown.
        # We get the object so we can present the user with the filename rather than the pk.
        self.current_value = None
        if initial:
            if isinstance(initial, ComponentInterfaceValue):
                # This can happen on display set or archive item update forms, the value is then taken from the model
                # instance unless the value is in the form data.
                self.current_value = initial
                initial = initial.pk
            # Otherwise the value is taken from the form data and will always take the form of a pk for either
            # a ComponentInterfaceValue object (in this case the pk is a digit) or
            # a UserUpload object (then the pk is a UUID).
            elif (
                isinstance(initial, int) or initial.isdigit()
            ) and ComponentInterfaceValue.objects.filter(pk=initial).exists():
                self.current_value = ComponentInterfaceValue.objects.get(
                    pk=initial
                )
            elif UserUpload.objects.filter(pk=initial).exists():
                self.current_value = UserUpload.objects.get(pk=initial)
            else:
                raise TypeError(f"Unknown type for initial value: {initial}")

        file_search_queryset = get_component_interface_values_for_user(
            user=self.user,
            interface=self.interface,
        )
        upload_queryset = get_objects_for_user(
            self.user,
            "uploads.change_userupload",
        ).filter(status=UserUpload.StatusChoices.COMPLETED)
        fields = [
            ModelChoiceField(queryset=file_search_queryset, required=False),
            ModelChoiceField(queryset=upload_queryset, required=False),
        ]
        super().__init__(
            *args,
            fields=fields,
            require_all_fields=False,
            initial=initial,
            **kwargs,
        )

    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs["current_value"] = self.current_value
        attrs["user"] = self.user
        attrs["widget_choices"] = {
            choice.name: choice.value for choice in FileWidgetChoices
        }
        return attrs

    def compress(self, values):
        if values:
            non_empty_values = [
                val for val in values if val and val not in self.empty_values
            ]
            if len(non_empty_values) != 1:
                raise ValidationError("Too many values returned.")
            return non_empty_values[0]
