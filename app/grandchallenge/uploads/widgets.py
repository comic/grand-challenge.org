from django.forms import HiddenInput


class UserUploadWidget(HiddenInput):
    template_name = "uploads/widget.html"

    class Media:
        js = ("js/user_upload.js",)
