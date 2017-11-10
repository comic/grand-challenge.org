import datetime

from django.forms.widgets import Widget
from django.http.request import HttpRequest
from django.http.response import HttpResponseBadRequest, \
    HttpResponseServerError, JsonResponse
from django.template.loader import get_template

from evaluation.models import StagedFile


class AjaxUploadWidget(Widget):
    """
    A widget that implements asynchronous file uploads for forms. It creates
    a list of database ids and adds them to the form using AJAX requests.

    To use this widget, a website must fulfill certain requirements:
     - The following JavaScript libraries must be loaded:
       - jQuery (3.2.1)
       - jQuery-ui (1.12.1)
       - blueimp-file-upload (9.19.1)
     - The website must include the JS and CSS files defined in the classes
       variables CSS and JS
     - The website must define a djang csfr-token by either:
       - defining a hidden input element with the name 'csrfmiddlewaretoken'
         (use the {% csrf_token %} template function for this).
       - define the csfr_token by defining the global javascript variable
         'upload_csrf_token'
     - For each widget a valid ajax-receiver must be installed. Each instance
       of an AjaxUploadWidget exposes the function 'handle_ajax' as handler
       for ajax requests. During initialization, the ajax-path must be
       defined using the 'ajax_target_path' named parameter

    Notes
    -----
    There are potential security risks with the implementation. First of all,
    uploads are not linked to any session or similar. Anyone who can guess
    a valid database id referring to a file, can also refer to this file. What
    this means depends on the actual app that uses this widget.
    """

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

        context = {}
        context["target"] = self.ajax_target_path
        context["value"] = "" if value in (None, "") else str(value)
        context["name"] = name
        context["attrs"] = attrs

        return template.render(context=context)
