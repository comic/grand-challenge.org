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
from grandchallenge.uploads.widgets import UserUploadMultipleWidget


class WidgetChoices(TextChoices):
    IMAGE_SEARCH = "IMAGE_SEARCH"
    IMAGE_UPLOAD = "IMAGE_UPLOAD"
    UNDEFINED = "UNDEFINED"


class ImageSearchWidget(ChoiceWidget, HiddenInput):
    template_name = "cases/image-search-widget.html"
    input_type = None
    name = None

    def __init__(self, *args, name=None, **kwargs):
        super().__init__(*args, **kwargs)
        if name:
            self.name = name

    def get_context(self, *args, **kwargs):
        context = super().get_context(*args, **kwargs)
        if self.name:
            context["widget"]["name"] = self.name
        return context


class FlexibleImageWidget(MultiWidget):
    template_name = "cases/flexible_image_widget.html"

    def __init__(
        self,
        *args,
        help_text=None,
        user=None,
        current_value=None,
        disabled=False,
        **kwargs,
    ):
        widgets = (
            ImageSearchWidget(),
            UserUploadMultipleWidget(),
        )
        super().__init__(widgets)
        self.attrs = {
            "help_text": help_text,
            "disabled": disabled,
            "user": user,
            "current_value": current_value,
            "widget_choices": {
                choice.name: choice.value for choice in WidgetChoices
            },
        }

    def decompress(self, value):
        if value:
            if value in WidgetChoices.names:
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
                value = data[f"WidgetChoice-{name}"]
            except KeyError:
                value = None
        if value:
            if value in WidgetChoices.names:
                return [None, None]
            elif Image.objects.filter(pk=value).exists():
                return [value, None]
            else:
                return [None, [value]]


class FlexibleImageField(MultiValueField):

    widget = FlexibleImageWidget

    def __init__(
        self,
        *args,
        require_all_fields=False,
        image_queryset=None,
        upload_queryset=None,
        disabled=False,
        **kwargs,
    ):
        list_fields = [
            ModelChoiceField(queryset=image_queryset),
            ModelMultipleChoiceField(queryset=upload_queryset),
        ]
        super().__init__(*args, fields=list_fields, **kwargs)
        self.require_all_fields = require_all_fields
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
