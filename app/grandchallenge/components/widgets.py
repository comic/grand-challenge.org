from django.forms import Select


class SelectUploadWidget(Select):
    template_name = "components/select_upload_widget.html"
