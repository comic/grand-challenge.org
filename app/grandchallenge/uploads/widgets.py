from django.forms.widgets import HiddenInput, MultipleHiddenInput


class UserUploadWidgetMixin:
    template_name = "uploads/widget.html"
    input_type = None

    class Media:
        css = {
            "all": (
                "https://releases.transloadit.com/uppy/v2.1.1/uppy.min.css",
            )
        }
        js = (
            "https://releases.transloadit.com/uppy/v2.1.1/uppy.min.js",
            "js/user_upload.js",
        )


class UserUploadSingleWidget(UserUploadWidgetMixin, HiddenInput):
    pass


class UserUploadMultipleWidget(UserUploadWidgetMixin, MultipleHiddenInput):
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["attrs"]["multiple"] = True
        return context
