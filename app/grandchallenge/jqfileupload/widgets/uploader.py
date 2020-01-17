import hashlib
import uuid
from io import BufferedIOBase

from django import forms
from django.core.exceptions import ValidationError
from django.forms.widgets import Widget
from django.http.request import HttpRequest
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
     - Add cleanup service call to cleanup_stale_files in a background worker
    """

    class Media:
        css = {"all": ("jqfileupload/css/upload_widget_button.css",)}
        js = ("jqfileupload/js/upload_widget.js",)

    def __init__(
        self, *args, multifile=True, auto_commit=True, user=None, **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.user = user
        self.__multifile = bool(multifile)
        self.__auto_commit = bool(auto_commit)

    @property
    def template_name(self):
        if self.__multifile:
            return "widgets/multi_uploader.html"
        else:
            return "widgets/single_uploader.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        if self.user is None:
            raise RuntimeError("The user must be set on the upload widget!")

        context.update(
            {
                "user": self.user,
                "multi_upload": "true" if self.__multifile else "false",
                "auto_commit": "true" if self.__auto_commit else "false",
            }
        )

        return context


class OpenedStagedAjaxFile(BufferedIOBase):
    """
    A open file handle for a :class:`StagedAjaxFile`.

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
    """File representation of the loose chunks that belong to a single file."""

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
        """The uuid-representation of the file used in the actual form."""
        return self.__uuid

    @property
    def name(self):
        """
        Returns the name specified by the client for the uploaded file (might
        be unsafe!).
        """
        chunks_query = self._raise_if_missing()
        return chunks_query.first().client_filename

    @property
    def exists(self):
        """True if the file has not been cleaned up yet."""
        return StagedFile.objects.filter(file_id=self.__uuid).exists()

    @property
    def size(self):
        """Total size of the file in bytes."""
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
        """False if the upload was incomplete or corrupted in another way."""
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
        for chunk in query:
            chunk.file.delete()
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
