from django.conf import settings
from django.forms import Script
from django.forms.widgets import HiddenInput, MultipleHiddenInput


class UserUploadWidgetMixin:
    template_name = "uploads/widget.html"
    input_type = None

    def __init__(self, *args, allowed_file_types=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_file_types = allowed_file_types

    def get_context(self, *args, **kwargs):
        context = super().get_context(*args, **kwargs)
        widget_id = f'X_{context["widget"]["attrs"]["id"]}'
        context["widget"]["attrs"]["id"] = widget_id
        context["widget"]["allowed_file_types"] = {
            "id": f"{widget_id}AllowedFileTypes",
            "value": self.allowed_file_types,
        }
        context["widget"]["attrs"]["max_number_files"] = 100
        return context

    class Media:
        css = {"all": ("vendored/uppy/uppy.min.css",)}
        js = (
            "vendored/uppy/uppy.min.js",
            Script("js/user_upload.mjs", type="module"),
        )


class UserUploadSingleWidget(UserUploadWidgetMixin, HiddenInput):
    pass


class UserUploadMultipleWidget(UserUploadWidgetMixin, MultipleHiddenInput):
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["attrs"]["multiple"] = True
        return context


class DICOMUserUploadMultipleWidget(UserUploadMultipleWidget):
    class Media:
        js = (
            "vendored/@diagnijmegen/rse-grand-challenge-dicom-de-id-procedure/dist/grand-challenge-dicom-de-id-procedure.umd.min.js",
            "vendored/dcmjs/build/dcmjs.min.js",
            Script(
                "js/dicom_deidentification.mjs",
                type="module",
            ),
        )

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            allowed_file_types=(
                "application/dicom",
                "application/octet-stream",  # many dicom files have this
            ),
            **kwargs,
        )

    def get_context(self, *args, **kwargs):
        context = super().get_context(*args, **kwargs)
        context["widget"]["attrs"][
            "max_number_files"
        ] = settings.CASES_MAX_NUM_USER_UPLOADS
        context["widget"]["type"] = "dicom"
        return context
