import datetime

from django.forms.widgets import Widget
from django.http.request import HttpRequest
from django.http.response import HttpResponseBadRequest, \
    HttpResponseServerError, JsonResponse
from django.template.loader import get_template

from evaluation.models import StagedFile


class AjaxUploadWidget(Widget):
    CSS = "/static/evaluation/upload_widget.css"
    JS = "/static/evaluation/upload_widget.js"

    TEMPLATE_ATTRS = dict(JS=JS, CSS=CSS)

    def __init__(
            self,
            *args,
            ajax_target_path: str=None,
            **kwargs):
        super(AjaxUploadWidget, self).__init__(*args, **kwargs)

        if ajax_target_path is None:
            raise ValueError("AJAX target path required")

        self.ajax_target_path = ajax_target_path
        self.timeout = datetime.timedelta(hours=2)

    def handle_ajax(self, request: HttpRequest):
        if request.method != "POST":
            return HttpResponseBadRequest()

        result = {}
        for uploaded_file in request.FILES.values():
            new_staged_file = StagedFile.objects.create(
                    timeout=datetime.datetime.utcnow() + self.timeout,
                    file=uploaded_file
                )
            result[uploaded_file.name] = new_staged_file.id

        return JsonResponse(result)

    def render(self, name, value, attrs=None):
        template = get_template("widgets/uploader.html")

        context = dict(attrs) if attrs else {}
        context["target"] = self.ajax_target_path

        return template.render(context=context)
