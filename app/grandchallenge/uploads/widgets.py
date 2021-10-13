from django.forms.widgets import HiddenInput, MultipleHiddenInput


class UserUploadWidgetMixin:
    template_name = "uploads/widget.html"
    input_type = None

    def __init__(self, *args, allowed_file_types=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_file_types = allowed_file_types

    def get_context(self, *args, **kwargs):
        context = super().get_context(*args, **kwargs)
        context["widget"]["allowed_file_types"] = {
            "id": f"{context['widget']['attrs']['id']}AllowedFileTypes",
            "value": self.allowed_file_types,
        }
        return context

    class Media:
        css = {
            "all": (
                "https://releases.transloadit.com/uppy/v2.2.0/uppy.min.css",
            )
        }
        js = (
            "https://releases.transloadit.com/uppy/v2.2.0/uppy.min.js",
            "js/user_upload.js",
        )


class UserUploadSingleWidget(UserUploadWidgetMixin, HiddenInput):
    pass


class UserUploadMultipleWidget(UserUploadWidgetMixin, MultipleHiddenInput):
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["attrs"]["multiple"] = True
        return context
