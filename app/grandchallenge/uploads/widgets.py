from django.forms import HiddenInput


class UserUploadWidget(HiddenInput):
    template_name = "uploads/widget.html"

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
