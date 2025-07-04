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
        return context

    class Media:
        css = {"all": ("vendored/uppy/uppy.min.css",)}
        js = (
            "vendored/@diagnijmegen/rse-grand-challenge-dicom-deid-procedure/dist/grand-challenge-dicom-de-id-procedure.umd.js",
            "vendored/dcmjs/build/dcmjs.js",
            "vendored/uppy/uppy.min.js",
            "js/file_preprocessors.js",
            "js/user_upload.js",
        )


class UserUploadSingleWidget(UserUploadWidgetMixin, HiddenInput):
    pass


class UserUploadMultipleWidget(UserUploadWidgetMixin, MultipleHiddenInput):
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["attrs"]["multiple"] = True
        return context
