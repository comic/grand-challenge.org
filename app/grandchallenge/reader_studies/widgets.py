from django.forms import Select


class SelectUploadWidget(Select):
    template_name = "reader_studies/select_upload_widget.html"
