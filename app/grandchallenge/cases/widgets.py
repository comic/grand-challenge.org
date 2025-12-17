from typing import NamedTuple
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import QuerySet, TextChoices
from django.forms import (
    CharField,
    ChoiceField,
    HiddenInput,
    ModelChoiceField,
    ModelMultipleChoiceField,
    MultiValueField,
    MultiWidget,
    Select,
    TextInput,
)
from django.forms.widgets import ChoiceWidget

from grandchallenge.cases.models import Image
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.core.guardian import (
    filter_by_permission,
    get_object_if_allowed,
)
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import (
    DICOMUserUploadMultipleWidget,
    UserUploadMultipleWidget,
)


class ImageWidgetChoices(TextChoices):
    UNDEFINED = "", "Choose data source..."
    IMAGE_SELECTED = "IMAGE_SELECTED", ""
    IMAGE_SEARCH = "IMAGE_SEARCH", "Select an existing image"
    IMAGE_UPLOAD = "IMAGE_UPLOAD", "Upload a new image"


class ImageSourceChoiceField(ChoiceField):
    widget = Select(attrs={"class": "custom-select"})

    def __init__(
        self,
        *args,
        current_socket_value=None,
        required=True,
        **kwargs,
    ):
        self.current_socket_value = current_socket_value

        choices = kwargs.pop("choices", [])

        if current_socket_value is None:
            choice = ImageWidgetChoices.UNDEFINED
            choices.append((choice.value, choice.label))
        else:
            choices.append(
                (
                    ImageWidgetChoices.IMAGE_SELECTED.value,
                    current_socket_value.title,
                )
            )

        for choice in [
            ImageWidgetChoices.IMAGE_SEARCH,
            ImageWidgetChoices.IMAGE_UPLOAD,
        ]:
            choices.append((choice.value, choice.label))

        super().__init__(
            *args,
            required=required,
            choices=choices,
            **kwargs,
        )

    def clean(self, value):
        value = super().clean(value)
        if value == ImageWidgetChoices.IMAGE_SELECTED:
            return self.current_socket_value.image
        else:
            return value


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

    def decompress(self, value):  # noqa: C901
        if not value:
            return [None, None]

        if isinstance(value, (list, tuple)):
            if len(value) == 1:
                item = value[0]
                if item == "":
                    return [None, None]
                if not item:
                    raise RuntimeError("Unexpected value")
                if item in ImageWidgetChoices.names:
                    return [None, None]
                if Image.objects.filter(pk=item).exists():
                    return [str(item), None]
                # can also just be a single UserUpload
                return [None, value]
            else:
                # can be a list of UserUploads
                return [None, value]

        if isinstance(value, UUID):
            # when an image or user upload is preselected as current_value
            if Image.objects.filter(pk=value).exists():
                return [value, None]
            elif UserUpload.objects.filter(pk=value).exists():
                return [None, [value]]
            else:
                return [None, None]

        raise RuntimeError("Unrecognized value type")

    def value_from_datadict(self, data, files, name):
        try:
            value = data.getlist(name)
        except AttributeError:
            value = data.get(name)

        return self.decompress(value)


class FlexibleImageField(MultiValueField):
    widget = FlexibleImageWidget

    def __init__(  # noqa C901
        self,
        *args,
        interface,
        user=None,
        initial=None,
        **kwargs,
    ):
        image_search_queryset = filter_by_permission(
            queryset=Image.objects.filter(
                dicom_image_set__isnull=not interface.is_dicom_image_kind
            ),
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

        # The `current_value` is added to the widget attrs to display an appropriate
        # title in the initial dropdown and to add the pk(s) as hidden input
        # in the widget template.
        self.current_value = None
        if initial:
            if isinstance(initial, ComponentInterfaceValue):
                # This can happen on display set or archive item update forms,
                # the value is then taken from the model instance
                # unless the value is in the form data.
                if user.has_perm("view_image", initial.image):
                    self.current_value = [initial.image]
                    initial = initial.image.pk
                else:
                    initial = None
            elif isinstance(initial, (list, tuple)):
                # It can be a list of UserUpload objects
                uploads = []
                for i in initial:
                    if isinstance(i, UserUpload):
                        uploads.append(i)
                    else:
                        if upload := get_object_if_allowed(
                            model=UserUpload,
                            pk=i,
                            user=user,
                            codename="change_userupload",
                        ):
                            uploads.append(upload)
                if len(uploads) != 0:
                    self.current_value = uploads

            # Otherwise the value is taken from the form data and will always take
            # the form of a pk for either an Image object or a UserUpload object.
            elif image := get_object_if_allowed(
                model=Image, pk=initial, user=user, codename="view_image"
            ):
                self.current_value = [image]
            elif upload := get_object_if_allowed(
                model=UserUpload,
                pk=initial,
                user=user,
                codename="change_userupload",
            ):
                self.current_value = [upload]
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

        if self.current_value:
            if len(self.current_value) == 1:
                attrs["display_name"] = self.current_value[0].title
            else:
                attrs["display_name"] = (
                    f"Recently uploaded image(s): {[upload.title for upload in self.current_value]}"
                )

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


DICOM_UPLOAD_WIDGET_SUFFIXES = ["dicom-image-name", "dicom-user-uploads"]


class DICOMUploadWithName(NamedTuple):
    name: str
    user_uploads: list[
        str
    ]  # UserUpload pks, as expected by DICOMUserUploadMultipleWidget


class DICOMImageSetNameInput(TextInput):
    template_name = "cases/dicom_image_set_name_input.html"


class DICOMUploadWidget(MultiWidget):
    def __init__(self, attrs=None):
        widgets = {
            DICOM_UPLOAD_WIDGET_SUFFIXES[0]: DICOMImageSetNameInput(),
            DICOM_UPLOAD_WIDGET_SUFFIXES[1]: DICOMUserUploadMultipleWidget(),
        }
        super().__init__(widgets, attrs)

    def decompress(self, value: DICOMUploadWithName):
        if value:
            return [
                value.name,
                value.user_uploads,
            ]
        return ["", []]


class DICOMUploadField(MultiValueField):
    widget = DICOMUploadWidget

    def __init__(self, *args, user, **kwargs):
        upload_qs = filter_by_permission(
            queryset=UserUpload.objects.all(),
            user=user,
            codename="change_userupload",
        ).filter(status=UserUpload.StatusChoices.COMPLETED)

        fields = [
            CharField(),
            ModelMultipleChoiceField(queryset=upload_qs),
        ]

        super().__init__(
            *args,
            fields=fields,
            **kwargs,
        )

    def compress(self, values: list[str, QuerySet[UserUpload]]):
        return DICOMUploadWithName(
            name=values[0] if values else "",
            user_uploads=[str(v.pk) for v in values[1]] if values else [],
        )
