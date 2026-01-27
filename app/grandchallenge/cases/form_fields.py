from django.conf import settings
from django.db.models import QuerySet, TextChoices
from django.forms import (
    CharField,
    ChoiceField,
    ModelChoiceField,
    ModelMultipleChoiceField,
    MultiValueField,
)

from grandchallenge.cases.models import Image
from grandchallenge.cases.widgets import (
    DICOMUploadWidget,
    DICOMUploadWithName,
    ImageSearchMultiWidget,
)
from grandchallenge.components.form_fields import SourceChoices
from grandchallenge.components.widgets import SourceSelect
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.uploads.models import UserUpload

DICOM_IMAGE_UPLOAD_HELP_TEXT = f"""
The total size of all files uploaded in a single session cannot exceed 10 GB.
A maximum of {settings.CASES_MAX_NUM_USER_UPLOADS} files can be uploaded per session.
Please only upload one series instance per session.
"""


class ImageSourceChoices(TextChoices):
    UNDEFINED = SourceChoices.UNDEFINED, "Choose data source..."
    SEARCH = SourceChoices.SEARCH, "Select an existing image"
    UPLOAD = SourceChoices.UPLOAD, "Upload a new image"


class ImageSourceChoiceField(ChoiceField):
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
        choices.extend(ImageSourceChoices.choices)

        if current_socket_value:
            choices.remove(
                (
                    ImageSourceChoices.UNDEFINED.value,
                    ImageSourceChoices.UNDEFINED.label,
                )
            )
            choices.insert(
                0,
                (
                    SourceChoices.CURRENT.value,
                    current_socket_value.title,
                ),
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
            return self.current_socket_value.image
        else:
            return value


class DICOMUploadField(MultiValueField):
    widget = DICOMUploadWidget

    def __init__(self, *args, user, **kwargs):
        upload_queryset = filter_by_permission(
            queryset=UserUpload.objects.all(),
            user=user,
            codename="change_userupload",
        ).filter(status=UserUpload.StatusChoices.COMPLETED)

        fields = [
            CharField(),
            ModelMultipleChoiceField(queryset=upload_queryset),
        ]

        super().__init__(
            *args,
            fields=fields,
            help_text=DICOM_IMAGE_UPLOAD_HELP_TEXT,
            **kwargs,
        )

    def compress(self, values: list[str, QuerySet[UserUpload]]):
        return DICOMUploadWithName(
            name=values[0] if values else "",
            user_uploads=[str(v.pk) for v in values[1]] if values else [],
        )


class ImageSearchMultiField(MultiValueField):
    def __init__(
        self, *args, user, interface, prefixed_interface_slug, **kwargs
    ):
        queryset = filter_by_permission(
            queryset=Image.objects.filter(
                dicom_image_set__isnull=not interface.is_dicom_image_kind
            ),
            user=user,
            codename="view_image",
        )
        fields = [
            CharField(),
            ModelChoiceField(queryset=queryset),
        ]
        widget = ImageSearchMultiWidget(
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
