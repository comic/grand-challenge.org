from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from grandchallenge.jqfileupload.models import StagedFile
from grandchallenge.jqfileupload.widgets.uploader import (
    generate_upload_path_hash
)


def filter_requires_request_argument(f):
    """
    Marker that will lead to upload_filters getting an extra kwarg, which is
    the HttpRequest for the processed file upload.
    """
    f._filter_marker_requires_request_object = True
    return f


@filter_requires_request_argument
def reject_duplicate_filenames(
    file: UploadedFile, request: HttpRequest = None
):
    """
    Upload filter that can be used together with
    AjaxUploadWidget-upload_filters. This filter will NOT work properly as a
    normal model-field filter! Using this filter will reject duplicate filenames
    while uploading the file.

    Parameters
    ----------
    file: UploadedFile
        The uploaded file object to check.
    request: HttpRequest
        Thee used HttpRequest

    Raises
    ------
    ValidationError:
        Raised if a duplicate file has been detected.

    """
    csrf_token = request.META.get("CSRF_COOKIE", None)
    client_id = request.META.get(
        "X-Upload-ID", request.POST.get("X-Upload-ID", None)
    )
    if csrf_token:
        uploaded_files = StagedFile.objects.filter(
            csrf=csrf_token,
            client_filename=file.name,
            upload_path_sha256=generate_upload_path_hash(request),
        )
        if client_id:
            uploaded_files = uploaded_files.exclude(client_id=client_id)
        if uploaded_files.exists():
            raise ValidationError("Duplicate file")
