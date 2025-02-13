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


class InterfaceFormField:
    _possible_widgets = {
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
        instance=None,
        user=None,
        required=True,
        initial=None,
        form_data=None,
        help_text="",
        disabled=False,
    ):
        self.instance = instance
        self.user = user
        self.required = required
        self.initial = initial
        self.form_data = form_data
        self.help_text = help_text
        self.disabled = disabled

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
                # This can happen on display set or archive item update forms, the value is then taken from the model
                # instance unless the value is in the form data.
                current_value = self.initial.image
            # Otherwise the value is taken from the form data and will always take the form of a pk for either
            # an Image object or a UserUpload object.
            # We get the object so we can present the user with the image name rather than the pk.
            elif Image.objects.filter(pk=self.initial).exists():
                current_value = Image.objects.get(pk=self.initial)
            elif UserUpload.objects.filter(pk=self.initial).exists():
                current_value = UserUpload.objects.get(pk=self.initial)
            else:
                raise TypeError(
                    f"Unknown type for initial value: {self.initial}"
                )

        self.kwargs["widget"] = FlexibleImageWidget(
            help_text=self.help_text,
            user=self.user,
            current_value=current_value,
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
                # This can happen on display set or archive item update forms, the value is then taken from the model
                # instance unless the value is in the form data.
                current_value = self.initial
            # Otherwise the value is taken from the form data and will always take the form of a pk for either
            # a ComponentInterfaceValue object (in this case the pk is a digit) or
            # a UserUpload object (then the pk is a UUID).
            # We get the object so we can present the user with the image name rather than the pk.
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
                raise TypeError(
                    f"Unknown type for initial value: {self.initial}"
                )

        self.kwargs["widget"] = FlexibleFileWidget(
            help_text=self.help_text,
            user=self.user,
            current_value=current_value,
        )
        return FlexibleFileField(
            user=self.user,
            interface=self.instance,
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
        user=None,
        interface=None,
        disabled=False,
        **kwargs,
    ):
        self.user = user
        self.interface = interface
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
