from uuid import UUID

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
from grandchallenge.core.guardian import (
    filter_by_permission,
    get_object_if_allowed,
)
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
        if not value:
            return [None, None]

        if isinstance(value, (list, tuple)):
            if len(value) == 1:
                item = value[0]
                if item in ImageWidgetChoices.names:
                    return [None, None]
                if Image.objects.filter(pk=item).exists():
                    return [str(item), None]
                # can also just be a single UserUpload
                return [None, value]
            else:
                # can be a list of UserUploads or
                # a single image UUID (when an image is preselected)
                return [None, value]

        if isinstance(value, UUID):
            # when an image is preselected as current_value
            if Image.objects.filter(pk=value).exists():
                return [value, None]

        raise RuntimeError("Unrecognized value type")

    def value_from_datadict(self, data, files, name):
        try:
            value = data.getlist(name)
        except KeyError:
            # this happens if the data comes from the DS create / update form
            try:
                value = data.getlist(f"widget-choice-{name}")
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
        image_search_queryset = filter_by_permission(
            queryset=Image.objects.all(),
            user=user,
            codename="view_image",
        )
        upload_queryset = filter_by_permission(
            queryset=UserUpload.objects.all(),
            user=user,
            codename="change_userupload",
        ).filter(status=UserUpload.StatusChoices.COMPLETED)
        list_fields = [
            ModelChoiceField(queryset=image_search_queryset, required=False),
            ModelMultipleChoiceField(queryset=upload_queryset, required=False),
        ]

        # The `current_value` is added to the widget attrs to display in the initial dropdown.
        # We get the object so we can present the user with the image name rather than the pk.
        self.current_value = None
        if initial:
            if isinstance(initial, ComponentInterfaceValue):
                # This can happen on display set or archive item update forms,
                # the value is then taken from the model instance
                # unless the value is in the form data.
                if user.has_perm("view_image", initial.image):
                    self.current_value = initial.image
                    initial = initial.image.pk
                else:
                    initial = None
            # Otherwise the value is taken from the form data and will always take
            # the form of a pk for either an Image object or a UserUpload object.
            elif image := get_object_if_allowed(
                model=Image, pk=initial, user=user, codename="view_image"
            ):
                self.current_value = image
            elif upload := get_object_if_allowed(
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
