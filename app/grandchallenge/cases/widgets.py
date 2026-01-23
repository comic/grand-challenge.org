from enum import StrEnum
from typing import NamedTuple

from django.forms import MultiWidget, TextInput

from grandchallenge.components.widgets import (
    SearchSelect,
    SearchWidgetSuffixes,
)
from grandchallenge.uploads.widgets import DICOMUserUploadMultipleWidget


class DICOMUploadWidgetSuffixes(StrEnum):
    NAME = "dicom-image-name"
    UPLOADS = "dicom-user-uploads"


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
            DICOMUploadWidgetSuffixes.NAME.value: DICOMImageSetNameInput(),
            DICOMUploadWidgetSuffixes.UPLOADS.value: DICOMUserUploadMultipleWidget(),
        }
        super().__init__(widgets, attrs)

    def decompress(self, value: DICOMUploadWithName):
        if value:
            return [
                value.name,
                value.user_uploads,
            ]
        return ["", []]


class ImageSearchInputWidget(TextInput):
    def get_context(self, name, value, attrs):
        attrs["placeholder"] = "Search by pk or image name"
        context = super().get_context(name, value, attrs)
        css_class = context["widget"]["attrs"].get("class", "")
        # When the MultiField marks the data invalid, the is-invalid class is
        # added to all subwidgets; however, the search input is never "invalid"
        # because that data will not be processed.
        context["widget"]["attrs"]["class"] = css_class.replace(
            "is-invalid", ""
        )
        return context


class ImageSearchMultiWidget(MultiWidget):
    template_name = "cases/image_search_multi_widget.html"

    def __init__(self, attrs=None, prefixed_interface_slug=None):
        widgets = {
            SearchWidgetSuffixes.INPUT.value: ImageSearchInputWidget(),
            SearchWidgetSuffixes.CHOICE.value: SearchSelect(
                attrs={"class": "custom-select"}
            ),
        }
        super().__init__(widgets, attrs)
        self.prefixed_interface_slug = prefixed_interface_slug

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["prefixed_interface_slug"] = self.prefixed_interface_slug
        return context

    def decompress(self, value):
        if value:
            return value
        return ["", ""]
