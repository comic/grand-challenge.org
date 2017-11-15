import re
import datetime

from collections import Iterable
import uuid
from pprint import pprint

from django import forms
from django.core.exceptions import ValidationError
from django.forms.widgets import Widget
from django.http.request import HttpRequest
from django.http.response import HttpResponseBadRequest, \
    HttpResponseServerError, JsonResponse, HttpResponseForbidden
from django.template.loader import get_template

from evaluation.models import StagedFile


def cleanup_stale_files():
    """
    Cleanup routine target function to be invoked repeatedly. It scans the
    database for stale uploaded files and deletes them.
    """
    now = datetime.datetime.utcnow()
    files_to_delete = StagedFile.objects.filter(timeout__lt=now).all()
    for file in files_to_delete:
        print(f"Deleting {file.id}...")
        file.delete()


class InvalidRequestException(Exception): pass


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
     - Add cleanup service call to cleanup_stale_files in a background worker

    Notes
    -----
    There are potential security risks with the implementation. First of all,
    uploads are not linked to any session or similar. Anyone who can guess
    a valid database id referring to a file, can also refer to this file. What
    this means depends on the actual app that uses this widget.

    This widget will require updating when moving forward from django 1.8.
    """

    CSS = "/static/evaluation/upload_widget.css"
    JS = "/static/evaluation/upload_widget.js"

    TEMPLATE_ATTRS = dict(JS=JS, CSS=CSS)

    def __init__(
            self,
            *args,
            ajax_target_path: str = None,
            **kwargs):
        super(AjaxUploadWidget, self).__init__(*args, **kwargs)

        if ajax_target_path is None:
            raise ValueError("AJAX target path required")

        self.ajax_target_path = ajax_target_path
        self.timeout = datetime.timedelta(hours=2)

    def _handle_complete(self, request, csrf_token, uploaded_file):
        # csrf = models.CharField(max_length=128)
        # client_id = models.CharField(max_length=128)
        #
        # file_id = models.UUIDField(blank=False)
        # timeout = models.DateTimeField(blank=False)
        #
        # file = models.FileField(blank=False)
        # start_byte = models.BigIntegerField(blank=False)
        # end_byte = models.BigIntegerField(blank=False)
        # total_size = models.BigIntegerField(blank=False)

        new_staged_file = StagedFile.objects.create(
            csrf=csrf_token,
            client_id=None,

            file_id=uuid.uuid4(),
            timeout=datetime.datetime.utcnow() + self.timeout,

            file=uploaded_file,
            start_byte=0,
            end_byte=uploaded_file.size,
            total_size=uploaded_file.size,
        )

        return {
            "filename": new_staged_file.file.name,
            "uuid": new_staged_file.file_id,
            "extra_attrs": {},
        }

    def _handle_chunked(self, request, csrf_token, uploaded_file):
        # Only content ranges of the form
        #
        #   bytes-unit SP byte-range-resp
        #
        # according to rfc7233 are accepted. See here:
        # https://tools.ietf.org/html/rfc7233#appendix-C
        range_header = request.META.get("HTTP_CONTENT_RANGE", None)
        if not range_header:
            raise InvalidRequestException("Client did not supply Content-Range")
        range_match = re.match(
            r"bytes (?P<start>[0-9]{1,32})-(?P<end>[0-9]{1,32})/(?P<length>\*|[0-9]{1,32})",
            range_header)
        if not range_header:
            raise InvalidRequestException("Supplied invalid Content-Range")
        start_byte = int(range_match.group("start"))
        end_byte = int(range_match.group("end"))
        if range_match.group("length") is None:
            total_size = None
        else:
            total_size = int(range_match.group("length"))
        if start_byte > end_byte:
            raise InvalidRequestException("Supplied invalid Content-Range")
        if end_byte - start_byte + 1 != uploaded_file.size:
            raise InvalidRequestException("Invalid start-end byte range")

        client_id = request.META.get(
            "X-Upload-ID",
            request.POST.get(
                "X-Upload-ID",
                None))
        if not client_id:
            raise InvalidRequestException("Client did not supply a X-Upload-ID")
        if len(client_id) > 128:
            raise InvalidRequestException("X-Upload-ID is too long")

        # Verify consistency and generate file ids
        other_chunks = StagedFile.objects.filter(
            csrf=csrf_token, client_id=client_id).all()
        if len(other_chunks) == 0:
            file_id = uuid.uuid4()
        else:
            chunk_intersects = other_chunks.filter(
                start_byte__lte=end_byte, end_byte__gte=start_byte).exists()
            if chunk_intersects:
                raise InvalidRequestException("Overlapping chunks")

            if total_size is not None:
                inconsistent_total_size = other_chunks.exclude(
                    total_size=None).exclude(
                    total_size=total_size).exists()
                if inconsistent_total_size:
                    raise InvalidRequestException("Inconsistent total size")

            file_id = other_chunks[0].file_id

        new_staged_file = StagedFile.objects.create(
            csrf=csrf_token,
            client_id=client_id,

            file_id=file_id,
            timeout=datetime.datetime.utcnow() + self.timeout,

            file=uploaded_file,
            start_byte=start_byte,
            end_byte=end_byte,
            total_size=total_size,
        )

        return {
            "filename": new_staged_file.file.name,
            "uuid": new_staged_file.file_id,
            "extra_attrs": {},
        }

    def handle_ajax(self, request: HttpRequest):
        if request.method != "POST":
            return HttpResponseBadRequest()

        csrf_token = request.META.get('CSRF_COOKIE', None)
        if not csrf_token:
            return HttpResponseForbidden("CSRF token is missing")

        if "HTTP_CONTENT_RANGE" in request.META:
            handler = self._handle_chunked
        else:
            handler = self._handle_complete

        result = []
        try:
            for uploaded_file in request.FILES.values():
                result.append(handler(request, csrf_token, uploaded_file))
        except InvalidRequestException as e:
            return HttpResponseBadRequest(str(e))

        return JsonResponse(result, safe=False)

    def render(self, name, value, attrs=None):
        template = get_template("widgets/uploader.html")

        if isinstance(value, Iterable):
            value = ",".join(str(x) for x in value)
        elif value in (None, ""):
            value = ""
        else:
            value = str(value)

        context = {
            "target": self.ajax_target_path,
            "value": value,
            "name": name,
            "attrs": attrs,
        }

        return template.render(context=context)


class UploadedAjaxFileList(forms.Field):
    def to_python(self, value):
        allowed_characters = '0123456789abcdefABCDEF-,'
        if any(c for c in value if c not in allowed_characters):
            raise ValidationError(
                "UUID list includes invalid cahracters")

        split_items = value.split(",")
        uuids = []
        for s in split_items:
            try:
                uuids.append(uuid.UUID(s))
            except ValueError:
                raise ValidationError(
                    "Not a valid UUID: %(string)s",
                    {"string": s})

        return uuids

    def prepare_value(self, value):
        # convert value to be stuffed into the html
        pass
