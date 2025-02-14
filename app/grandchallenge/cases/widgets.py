from django.core.exceptions import ValidationError
from django.db.models import TextChoices
from django.forms import (
    HiddenInput,
    ModelChoiceField,
    ModelMultipleChoiceField,
    MultiValueField,
    MultiWidget,
)
from django.forms.widgets import ChoiceWidget

from grandchallenge.cases.models import Image
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.core.guardian import get_objects_for_user
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import UserUploadMultipleWidget


class ImageWidgetChoices(TextChoices):
    IMAGE_SEARCH = "IMAGE_SEARCH"
    IMAGE_UPLOAD = "IMAGE_UPLOAD"
    IMAGE_SELECTED = "IMAGE_SELECTED"
    UNDEFINED = "UNDEFINED"


class ImageSearchWidget(ChoiceWidget, HiddenInput):
    template_name = "cases/image_search_widget.html"
    input_type = None
    name = None

    def __init__(self, *args, name=None, **kwargs):
        super().__init__(*args, **kwargs)
        if name:
            self.name = name

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if self.name:
            context["widget"]["name"] = self.name
        return context


class FlexibleImageWidget(MultiWidget):
    template_name = "cases/flexible_image_widget.html"

    def __init__(
        self,
        attrs=None,
    ):
        widgets = (
            ImageSearchWidget(),
            UserUploadMultipleWidget(),
        )
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            if value in ImageWidgetChoices.names:
                return [None, None]
            elif Image.objects.filter(pk=value).exists():
                return [value, None]
            else:
                return [None, [value]]
        else:
            return [None, None]

    def value_from_datadict(self, data, files, name):
        try:
            value = data[name]
        except KeyError:
            # this happens if the data comes from the DS create / update form
            try:
                value = data[f"widget-choice-{name}"]
            except KeyError:
                value = None
        return self.decompress(value)


class FlexibleImageField(MultiValueField):

    widget = FlexibleImageWidget

    def __init__(
        self,
        *args,
        user=None,
        initial=None,
        **kwargs,
    ):
        # The `current_value` is added to the widget attrs to display in the initial dropdown.
        # We get the object so we can present the user with the image name rather than the pk.
        self.current_value = None
        if initial:
            if isinstance(initial, ComponentInterfaceValue):
                # This can happen on display set or archive item update forms, the value is then taken from the model
                # instance unless the value is in the form data.
                self.current_value = initial.image
                initial = initial.image.pk
            # Otherwise the value is taken from the form data and will always take the form of a pk for either
            # an Image object or a UserUpload object.
            elif Image.objects.filter(pk=initial).exists():
                self.current_value = Image.objects.get(pk=initial)
            elif UserUpload.objects.filter(pk=initial).exists():
                self.current_value = UserUpload.objects.get(pk=initial)
            else:
                raise TypeError(f"Unknown type for initial value: {initial}")

        upload_queryset = get_objects_for_user(
            user,
            "uploads.change_userupload",
        ).filter(status=UserUpload.StatusChoices.COMPLETED)
        image_queryset = get_objects_for_user(user, "cases.view_image")
        list_fields = [
            ModelChoiceField(queryset=image_queryset, required=False),
            ModelMultipleChoiceField(queryset=upload_queryset, required=False),
        ]
        super().__init__(
            *args,
            fields=list_fields,
            initial=initial,
            require_all_fields=False,
            **kwargs,
        )

    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs["current_value"] = self.current_value
        attrs["widget_choices"] = {
            choice.name: choice.value for choice in ImageWidgetChoices
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
