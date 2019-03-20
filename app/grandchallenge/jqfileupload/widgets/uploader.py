import os
import re
import uuid
import json
import hashlib

from collections import Iterable
from datetime import timedelta
from io import BufferedIOBase
from tempfile import TemporaryFile

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.uploadedfile import UploadedFile
from django.forms.widgets import Widget
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.http.response import (
    HttpResponseBadRequest,
    JsonResponse,
    HttpResponseForbidden,
)
from django.template.loader import get_template
from django.utils import timezone

from grandchallenge.jqfileupload.models import StagedFile
from grandchallenge.jqfileupload.widgets.utils import IntervalMap


def generate_upload_path_hash(request: HttpRequest) -> str:
    hasher = hashlib.sha256()
    hasher.update(request.get_full_path().encode())
    return hasher.hexdigest()


def cleanup_stale_files():
    """
    Cleanup routine target function to be invoked repeatedly. It scans the
    database for stale uploaded files and deletes them.
    """
    now = timezone.now()
    chunks_to_delete = StagedFile.objects.filter(timeout__lt=now).all()
    for chunk in chunks_to_delete:
        chunk.file.delete()
        chunk.delete()


class NotFoundError(FileNotFoundError):
    pass


class InvalidRequestException(Exception):
    pass


class AjaxUploadWidget(Widget):
    """
    A widget that implements asynchronous file uploads for forms. It creates
    a list of database ids and adds them to the form using AJAX requests.

    To use this widget, a website must fulfill certain requirements:
     - The following JavaScript libraries must be loaded:
       - jQuery (3.2.1)
       - jQuery-ui (1.12.1)
       - blueimp-file-upload (9.19.1)
     - The website must render the media associated with the widget
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
    """

    class Media:
        css = {"all": ("jqfileupload/css/upload_widget_button.css",)}
        js = ("jqfileupload/js/upload_widget.js",)

    def __init__(
        self,
        *args,
        ajax_target_path: str = None,
        multifile=True,
        auto_commit=True,
        upload_validators=(),
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        if ajax_target_path is None:
            raise ValueError("AJAX target path required")

        self.ajax_target_path = ajax_target_path
        self.timeout = timedelta(hours=2)
        self.__multifile = bool(multifile)
        self.__auto_commit = bool(auto_commit)
        self.__upload_validators = tuple(upload_validators)

    def _handle_complete(
        self,
        request: HttpRequest,
        csrf_token: str,
        uploaded_file: UploadedFile,
    ) -> dict:
        new_staged_file = StagedFile.objects.create(
            csrf=csrf_token,
            client_id=None,
            client_filename=uploaded_file.name,
            file_id=uuid.uuid4(),
            timeout=timezone.now() + self.timeout,
            file=uploaded_file,
            start_byte=0,
            end_byte=uploaded_file.size - 1,
            total_size=uploaded_file.size,
            upload_path_sha256=generate_upload_path_hash(request),
        )
        return {
            "filename": new_staged_file.client_filename,
            "uuid": new_staged_file.file_id,
            "extra_attrs": {},
        }

    def _handle_chunked(
        self,
        request: HttpRequest,
        csrf_token: str,
        uploaded_file: UploadedFile,
    ) -> dict:
        # Only content ranges of the form
        #
        #   bytes-unit SP byte-range-resp
        #
        # according to rfc7233 are accepted. See here:
        # https://tools.ietf.org/html/rfc7233#appendix-C
        range_header = request.META.get("HTTP_CONTENT_RANGE", None)
        if not range_header:
            raise InvalidRequestException(
                "Client did not supply Content-Range"
            )

        range_match = re.match(
            r"bytes (?P<start>[0-9]{1,32})-(?P<end>[0-9]{1,32})/(?P<length>\*|[0-9]{1,32})",
            range_header,
        )
        if not range_match:
            raise InvalidRequestException("Supplied invalid Content-Range")

        start_byte = int(range_match.group("start"))
        end_byte = int(range_match.group("end"))
        if (range_match.group("length") is None) or (
            range_match.group("length") == "*"
        ):
            total_size = None
        else:
            total_size = int(range_match.group("length"))
        if start_byte > end_byte:
            raise InvalidRequestException("Supplied invalid Content-Range")

        if (total_size is not None) and (end_byte >= total_size):
            raise InvalidRequestException("End byte exceeds total file size")

        if end_byte - start_byte + 1 != uploaded_file.size:
            raise InvalidRequestException("Invalid start-end byte range")

        client_id = request.META.get(
            "X-Upload-ID", request.POST.get("X-Upload-ID", None)
        )
        if not client_id:
            raise InvalidRequestException(
                "Client did not supply a X-Upload-ID"
            )

        if len(client_id) > 128:
            raise InvalidRequestException("X-Upload-ID is too long")

        # Verify consistency and generate file ids
        other_chunks = StagedFile.objects.filter(
            csrf=csrf_token,
            client_id=client_id,
            upload_path_sha256=generate_upload_path_hash(request),
        ).all()
        if len(other_chunks) == 0:
            file_id = uuid.uuid4()
        else:
            chunk_intersects = other_chunks.filter(
                start_byte__lte=end_byte, end_byte__gte=start_byte
            ).exists()
            if chunk_intersects:
                raise InvalidRequestException("Overlapping chunks")

            inconsistent_filenames = other_chunks.exclude(
                client_filename=uploaded_file.name
            ).exists()
            if inconsistent_filenames:
                raise InvalidRequestException(
                    "Chunks have inconsistent filenames"
                )

            if total_size is not None:
                inconsistent_total_size = (
                    other_chunks.exclude(total_size=None)
                    .exclude(total_size=total_size)
                    .exists()
                )
                if inconsistent_total_size:
                    raise InvalidRequestException("Inconsistent total size")

            file_id = other_chunks[0].file_id
        new_staged_file = StagedFile.objects.create(
            csrf=csrf_token,
            client_id=client_id,
            client_filename=uploaded_file.name,
            file_id=file_id,
            timeout=timezone.now() + self.timeout,
            file=uploaded_file,
            start_byte=start_byte,
            end_byte=end_byte,
            total_size=total_size,
            upload_path_sha256=generate_upload_path_hash(request),
        )
        return {
            "filename": new_staged_file.client_filename,
            "uuid": new_staged_file.file_id,
            "extra_attrs": {},
        }

    def handle_ajax(self, request: HttpRequest, **kwargs) -> HttpResponse:
        if request.method != "POST":
            return HttpResponseBadRequest()

        csrf_token = request.META.get("CSRF_COOKIE", None)
        if not csrf_token:
            return HttpResponseForbidden(
                "CSRF token is missing", content_type="text/plain"
            )

        if "HTTP_CONTENT_RANGE" in request.META:
            handler = self._handle_chunked
        else:
            handler = self._handle_complete
        result = []
        try:
            for uploaded_file in request.FILES.values():
                try:
                    self.__validate_uploaded_file(request, uploaded_file)
                except ValidationError as e:
                    print(e, type(e))
                    return HttpResponseForbidden(
                        json.dumps(list(e.messages)),
                        content_type="application/json",
                    )

            for uploaded_file in request.FILES.values():
                result.append(handler(request, csrf_token, uploaded_file))
        except InvalidRequestException as e:
            return HttpResponseBadRequest(str(e))

        return JsonResponse(result, safe=False)

    def render(self, name, value, attrs=None, renderer=None):
        if self.__multifile:
            template = get_template("widgets/multi_uploader.html")
        else:
            template = get_template("widgets/single_uploader.html")
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
            "multi_upload": "true" if self.__multifile else "false",
            "auto_commit": "true" if self.__auto_commit else "false",
        }
        return template.render(context=context)

    def __validate_uploaded_file(self, request, uploaded_file):
        for validator in self.__upload_validators:
            kwargs = {}
            if hasattr(validator, "_filter_marker_requires_request_object"):
                # noinspection PyProtectedMember
                if validator._filter_marker_requires_request_object:
                    kwargs["request"] = request
            validator(uploaded_file, **kwargs)


class OpenedStagedAjaxFile(BufferedIOBase):
    """
    This class behaves like a file handle for a :class:`StagedAjaxFile`.
    The file handle is strictly read-only. Under the hood, this class
    reconstructs the contingent file from the file chunks that have been
    uploaded.
    """

    def __init__(self, _uuid):
        super().__init__()
        self._uuid = _uuid
        self._chunks = list(
            StagedFile.objects.filter(file_id=self._uuid).all()
        )
        self._chunks.sort(key=lambda x: x.start_byte)
        self._chunk_map = IntervalMap()
        for chunk in self._chunks:
            self._chunk_map.append_interval(
                chunk.end_byte - chunk.start_byte + 1, chunk
            )
        self._file_pointer = 0
        self._current_chunk = None

    @property
    def closed(self):
        return self._chunks is None

    @property
    def size(self):
        if self.closed:
            return None

        else:
            return len(self._chunk_map)

    def readable(self, *args, **kwargs):
        return True

    def writable(self, *args, **kwargs):
        return False

    def seekable(self, *args, **kwargs):
        return True

    def readinto(self, buffer):
        read_bytes = self.read(len(buffer))
        buffer[: len(read_bytes)] = read_bytes
        return len(read_bytes)

    def read(self, size=-1):
        if size < 0:
            size = None
        if self.closed:
            raise ValueError("file closed")

        if self.size <= self._file_pointer:
            return b""

        if self._file_pointer < 0:
            raise IOError("invalid file pointer position")

        if size is None:
            size = self.size - self._file_pointer
        result = b""
        while len(result) < size:
            if self._file_pointer >= len(self._chunk_map):
                break

            this_chunk = self._chunk_map[self._file_pointer]
            if this_chunk is not self._current_chunk:
                # we need to switch to a new chunk
                if self._current_chunk is not None:
                    self._current_chunk.file.close()
                    self._current_chunk = None
                this_chunk.file.open("rb")
                this_chunk.file.seek(
                    self._file_pointer - this_chunk.start_byte
                )
                self._current_chunk = this_chunk
            read_size = min(
                size - len(result),
                self._current_chunk.end_byte + 1 - self._file_pointer,
            )
            result += self._current_chunk.file.read(read_size)
            self._file_pointer += read_size
        return result

    def read1(self, size=-1):
        return self.read(size=size)

    def readinto1(self, buffer):
        return self.readinto(buffer)

    def seek(self, offset, from_what=0):
        if self.closed:
            raise ValueError("file closed")

        new_pointer = None
        if from_what == 0:
            new_pointer = offset
        elif from_what == 1:
            new_pointer = self._file_pointer + offset
        elif from_what == 2:
            new_pointer = self.size + offset
        if new_pointer < 0:
            raise IOError("invalid file pointer")

        self._file_pointer = new_pointer
        if self._file_pointer < self._chunk_map.len:
            if self._chunk_map[self._file_pointer] is self._current_chunk:
                self._current_chunk.file.seek(
                    self._file_pointer - self._current_chunk.start_byte
                )
        return self._file_pointer

    def tell(self, *args, **kwargs):
        if self.closed:
            raise ValueError("file closed")

        return self._file_pointer

    def close(self):
        if not self.closed:
            self._chunks = None
            if self._current_chunk is not None:
                self._current_chunk.file.close()
                self._current_chunk = None


class StagedAjaxFile:
    """
    File representation of otherwise loose chnks that belong to a single file.
    """

    def __init__(self, _uuid: uuid.UUID):
        super().__init__()
        if not isinstance(_uuid, uuid.UUID):
            raise TypeError("uuid parameter must be uuid.UUID")

        self.__uuid = _uuid

    def _raise_if_missing(self):
        query = StagedFile.objects.filter(file_id=self.__uuid)
        if not query.exists():
            raise NotFoundError()

        return query

    @property
    def uuid(self):
        """ The uuid-representation of the file used in the actual form """
        return self.__uuid

    @property
    def name(self):
        """ Returns the name specified by the client for the uploaded file
        (might be unsafe!) """
        chunks_query = self._raise_if_missing()
        return chunks_query.first().client_filename

    @property
    def exists(self):
        """ True if the file has not been cleaned up yet """
        return StagedFile.objects.filter(file_id=self.__uuid).exists()

    @property
    def size(self):
        """ Total size of the file in bytes """
        chunks_query = self._raise_if_missing()
        chunks = chunks_query.all()
        remaining_size = None
        # Check if we want to verify some total size
        total_sized_chunks = chunks.exclude(total_size=None)
        if total_sized_chunks.exists():
            remaining_size = total_sized_chunks.first().total_size
        current_size = 0
        for chunk in sorted(chunks, key=lambda x: x.start_byte):
            if chunk.start_byte != current_size:
                return None

            current_size = chunk.end_byte + 1
            if remaining_size is not None:
                remaining_size -= chunk.end_byte - chunk.start_byte + 1
        if remaining_size is not None:
            if remaining_size != 0:
                return None

        return current_size

    @property
    def is_complete(self):
        """  False if the upload was incomplete or corrupted in another way """
        if not StagedFile.objects.filter(file_id=self.__uuid).exists():
            return False

        return self.size is not None

    def open(self):
        """
        Opens a file handle-like object for reading the file. Opens in read mode.

        Returns
        -------
        :class:`OpenedStagedAjaxFile` represeting the opened file.
        """
        if not self.is_complete:
            raise IOError("incomplete upload")

        return OpenedStagedAjaxFile(self.__uuid)

    def delete(self):
        query = self._raise_if_missing()
        dir_name = None
        for chunk in query:
            if dir_name is None:
                dir_name = os.path.dirname(
                    os.path.join(settings.MEDIA_ROOT, chunk.file.name)
                )
            chunk.file.delete()
        if dir_name and os.path.isdir(dir_name):
            try:
                os.rmdir(dir_name)
            except IOError:
                pass  # Swallow all errors of rmdir
        query.delete()


class UploadedAjaxFileList(forms.Field):
    def to_python(self, value):
        if value is None:
            value = ""
        allowed_characters = "0123456789abcdefABCDEF-,"
        if any(c for c in value if c not in allowed_characters):
            raise ValidationError("UUID list includes invalid characters")

        split_items = value.split(",")
        uuids = []
        for s in split_items:
            try:
                uuids.append(uuid.UUID(s))
            except ValueError:
                raise ValidationError(
                    "Not a valid UUID: %(string)s", {"string": s}
                )

        return [StagedAjaxFile(uid) for uid in uuids]

    def prepare_value(self, value):
        # convert value to be stuffed into the html, this must be
        # implemented if we want to pre-populate upload forms
        return None
