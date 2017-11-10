from django.forms.widgets import Widget
from django.template.loader import get_template


class AjaxUploadWidget(Widget):
    CSS = "/static/evaluation/upload_widget.css"
    JS = "/static/evaluation/upload_widget.js"

    TEMPLATE_ATTRS = dict(JS=JS, CSS=CSS)

    def __init__(self,
            *args,
            ajax_target_path: str=None,
            **kwargs):
        super(AjaxUploadWidget, self).__init__(*args, **kwargs)

        if ajax_target_path is None:
            raise ValueError("AJAX target path required")
        self.ajax_target_path = ajax_target_path

    def render(self, name, value, attrs=None):
        template = get_template("widgets/uploader.html")
        return template.render({"target": self.ajax_target_path})
