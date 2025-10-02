from django import forms
from django.core.exceptions import ValidationError
from django.db.models import TextChoices
from django.forms import ModelChoiceField, MultiValueField

from grandchallenge.cases.widgets import (
    DICOMUploadField,
    FlexibleImageField,
    FlexibleImageWidget,
    ImageSearchWidget,
)
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.components.schemas import generate_component_json_schema
from grandchallenge.components.widgets import (
    FileSearchWidget,
    FlexibleFileWidget,
)
from grandchallenge.core.guardian import (
    filter_by_permission,
    get_object_if_allowed,
)
from grandchallenge.core.templatetags.bleach import clean
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

    def __new__(
        cls,
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

        kwargs = {
            "required": required,
            "help_text": clean(interface.description),
            "disabled": disabled,
            "label": interface.title.title(),
        }

        if interface.super_kind == interface.SuperKind.IMAGE:
            if interface.is_dicom_image_kind:
                return DICOMUploadField(
                    user=user,
                    initial=initial,
                    **kwargs,
                )
            else:
                return FlexibleImageField(
                    user=user,
                    initial=initial,
                    **kwargs,
                )
        elif interface.super_kind == interface.SuperKind.FILE:
            return FlexibleFileField(
                user=user,
                interface=interface,
                initial=initial,
                **kwargs,
            )
        elif interface.super_kind == interface.SuperKind.VALUE:
            return cls.get_json_field(
                interface=interface,
                initial=initial,
                **kwargs,
            )
        else:
            raise NotImplementedError(f"Unknown interface kind: {interface}")

    @staticmethod
    def get_json_field(interface, initial, **kwargs):
        if isinstance(initial, ComponentInterfaceValue):
            initial = initial.value
        kwargs["initial"] = initial
        field_type = interface.default_field

        schema = generate_component_json_schema(
            component_interface=interface,
            required=kwargs["required"],
        )

        if field_type == forms.JSONField:
            kwargs["widget"] = JSONEditorWidget(schema=schema)
        kwargs["validators"] = [JSONValidator(schema=schema)]

        return field_type(**kwargs)


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
        file_search_queryset = get_component_interface_values_for_user(
            user=user,
            interface=interface,
        )
        upload_queryset = filter_by_permission(
            queryset=UserUpload.objects.all(),
            user=user,
            codename="change_userupload",
        ).filter(status=UserUpload.StatusChoices.COMPLETED)
        fields = [
            ModelChoiceField(queryset=file_search_queryset, required=False),
            ModelChoiceField(queryset=upload_queryset, required=False),
        ]

        # The `current_value` is added to the widget attrs to display in the initial dropdown.
        # We get the object so we can present the user with the filename rather than the pk.
        self.current_value = None
        if initial:
            if isinstance(initial, ComponentInterfaceValue):
                # This can happen on display set or archive item update forms,
                # the value is then taken from the model instance
                # unless the value is in the form data.
                initial = initial.pk
            # Otherwise, the value is taken from the form data and will always take
            # the form of a pk for either
            # a ComponentInterfaceValue object (in this case the pk is a digit) or
            # a UserUpload object (then the pk is a UUID).
            if isinstance(initial, int) or initial.isdigit():
                if file_search_queryset.filter(pk=initial).exists():
                    self.current_value = file_search_queryset.get(pk=initial)
                else:
                    initial = None
            else:
                if upload := get_object_if_allowed(
                    model=UserUpload,
                    pk=initial,
                    user=user,
                    codename="change_userupload",
                ):
                    self.current_value = upload
                else:
                    initial = None

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
