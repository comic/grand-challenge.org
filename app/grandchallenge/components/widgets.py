from django.db.models import TextChoices
from django.forms import HiddenInput, MultiWidget
from django.forms.widgets import ChoiceWidget

from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import UserUploadSingleWidget


class FileWidgetChoices(TextChoices):
    FILE_SEARCH = "FILE_SEARCH"
    FILE_UPLOAD = "FILE_UPLOAD"
    FILE_SELECTED = "FILE_SELECTED"
    UNDEFINED = "UNDEFINED"


class FileSearchWidget(ChoiceWidget, HiddenInput):
    template_name = "components/file_search_widget.html"
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


class FlexibleFileWidget(MultiWidget):
    template_name = "components/flexible_file_widget.html"

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
            FileSearchWidget(),
            UserUploadSingleWidget(),
        )
        super().__init__(widgets)
        self.attrs = {
            "help_text": help_text,
            "disabled": disabled,
            "user": user,
            "current_value": current_value,
            "widget_choices": {
                choice.name: choice.value for choice in FileWidgetChoices
            },
        }

    def decompress(self, value):
        if value:
            if (
                isinstance(value, int) or value.isdigit()
            ) and ComponentInterfaceValue.objects.filter(pk=value).exists():
                return [value, None]
            elif UserUpload.objects.filter(pk=value).exists():
                return [None, value]
            else:
                return [None, None]
        else:
            return [None, None]

    def value_from_datadict(self, data, files, name):
        value = data.get(name)
        return self.decompress(value)
