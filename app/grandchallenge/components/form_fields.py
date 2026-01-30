from django.db.models import TextChoices
from django.forms import (
    BoundField,
    CharField,
    ChoiceField,
    ModelChoiceField,
    MultiValueField,
)

from grandchallenge.components.models import SourceChoices
from grandchallenge.components.widgets import (
    FileSearchMultiWidget,
    SourceSelect,
)
from grandchallenge.serving.models import (
    get_component_interface_values_for_user,
)


class FileSourceChoices(TextChoices):
    UNDEFINED = SourceChoices.UNDEFINED, "Choose data source..."
    SEARCH = SourceChoices.SEARCH, "Select an existing file"
    UPLOAD = SourceChoices.UPLOAD, "Upload a new file"
    REMOVE = SourceChoices.REMOVE, "⚠ Remove this file"


class BoundFieldWithDNoneClass(BoundField):
    def css_classes(self, extra_classes=None):
        return f"d-none {super().css_classes(extra_classes)}"


class FileSourceChoiceField(ChoiceField):
    widget = SourceSelect(attrs={"class": "custom-select"})

    def __init__(
        self,
        *args,
        current_socket_value=None,
        required=True,
        **kwargs,
    ):
        self.current_socket_value = current_socket_value

        choices = kwargs.pop("choices", [])
        choices.extend(FileSourceChoices.choices)

        if current_socket_value:
            choices.remove(
                (
                    FileSourceChoices.UNDEFINED.value,
                    FileSourceChoices.UNDEFINED.label,
                )
            )
            choices.insert(
                0,
                (
                    SourceChoices.CURRENT.value,
                    current_socket_value.title,
                ),
            )
        else:
            choices.remove(
                (
                    FileSourceChoices.REMOVE.value,
                    FileSourceChoices.REMOVE.label,
                )
            )

        super().__init__(
            *args,
            required=required,
            choices=choices,
            **kwargs,
        )

    def clean(self, value):
        value = super().clean(value)
        if value == SourceChoices.CURRENT:
            return self.current_socket_value
        else:
            return value


class FileSearchMultiField(MultiValueField):
    def __init__(
        self, *args, user, interface, prefixed_interface_slug, **kwargs
    ):
        queryset = get_component_interface_values_for_user(
            user=user,
            interface=interface,
        )
        fields = [
            CharField(),
            ModelChoiceField(queryset=queryset),
        ]
        widget = FileSearchMultiWidget(
            prefixed_interface_slug=prefixed_interface_slug
        )
        super().__init__(
            *args,
            fields=fields,
            widget=widget,
            **kwargs,
        )

    def clean(self, value):
        try:
            value = value[1]
        except IndexError:
            value = None

        self.fields[1].required = self.required

        return self.fields[1].clean(value)

    def compress(self, values):
        return values
