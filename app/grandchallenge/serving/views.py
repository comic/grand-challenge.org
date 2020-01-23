import posixpath
import re

from django.conf import settings
from django.http import Http404, HttpResponse
from django.utils._os import safe_join
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from grandchallenge.cases.models import Image
from grandchallenge.core.storage import ProtectedS3Storage
from grandchallenge.evaluation.models import Submission
from grandchallenge.serving.permissions import (
    user_can_download_image,
    user_can_download_submission,
)


def protected_storage_redirect(*, name):
    # Get the storage with the internal redirect and auth. This will prepend
    # settings.PROTECTED_S3_STORAGE_KWARGS['endpoint_url'] to the url
    storage = ProtectedS3Storage(internal=True)

    if not storage.exists(name=name):
        raise Http404("File not found.")

    url = storage.url(name=name)

    # Now strip the endpoint_url
    external_url = re.match(
        f"^{settings.PROTECTED_S3_STORAGE_KWARGS['endpoint_url']}(.*)$", url
    ).group(1)

    response = HttpResponse()
    response["X-Accel-Redirect"] = external_url

    return response


def serve_images(request, *, pk, path):
    document_root = safe_join(f"/{settings.IMAGE_FILES_SUBDIRECTORY}", str(pk))
    path = posixpath.normpath(path).lstrip("/")
    name = safe_join(document_root, path)

    try:
        image = Image.objects.get(pk=pk)
    except Image.DoesNotExist:
        raise Http404("File not found.")

    try:
        user, _ = TokenAuthentication().authenticate(request)
    except (AuthenticationFailed, TypeError):
        user = request.user

    if user_can_download_image(user=user, image=image):
        return protected_storage_redirect(name=name)

    raise Http404("File not found.")


def serve_submissions(request, *, submission_pk, **_):
    try:
        submission = Submission.objects.get(pk=submission_pk)
    except Submission.DoesNotExist:
        raise Http404("File not found.")

    if user_can_download_submission(user=request.user, submission=submission):
        return protected_storage_redirect(name=submission.file.name)

    raise Http404("File not found.")
