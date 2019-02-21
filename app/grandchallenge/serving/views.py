import os
import posixpath
import re

from django.conf import settings
from django.core.files import File
from django.core.files.storage import DefaultStorage
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils._os import safe_join
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from grandchallenge.cases.models import Image
from grandchallenge.challenges.models import Challenge
from grandchallenge.core.storage import ProtectedS3Storage
from grandchallenge.evaluation.models import Submission
from grandchallenge.serving.api import serve_file
from grandchallenge.serving.permissions import (
    can_access,
    user_can_download_image,
    user_can_download_submission,
)


def serve_fullpath(*, fullpath):
    storage = DefaultStorage()

    if not (os.path.abspath(fullpath) == fullpath) or not storage.exists(
        fullpath
    ):
        raise Http404("File not found.")

    try:
        f = storage.open(fullpath, "rb")
        file = File(f)
        return serve_file(file, save_as=True)
    except IOError:
        raise Http404("File not found.")


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


def serve_folder(request, *, challenge_name=None, folder=None, path):
    """
    Serve static files in a folder.

    If the file is in a challenge folder, then the subfolders of this challenge
    will be checked for permissions, see `can_access`.

    If the challenge_short_name is not set, then the folder must be set.
    ALL FILES IN THIS FOLDER WILL BE AVAILABLE TO DOWNLOAD.
    """
    path = posixpath.normpath(path).lstrip("/")

    if challenge_name:
        if folder:
            raise AttributeError("Only challenge_name or folder should be set")

        challenge = get_object_or_404(
            Challenge, short_name__iexact=challenge_name
        )

        document_root = safe_join(settings.MEDIA_ROOT, challenge.short_name)
        fullpath = safe_join(document_root, path)
        allowed = can_access(
            request.user,
            fullpath[len(document_root) :].lstrip("/"),
            challenge=challenge,
        )
    elif folder:
        document_root = safe_join(settings.MEDIA_ROOT, folder)
        fullpath = safe_join(document_root, path)
        allowed = True
    else:
        raise AttributeError("challenge_name or folder must be set")

    if not allowed:
        raise Http404("File not found.")

    return serve_fullpath(fullpath=fullpath)


def serve_images(request, *, pk, path):
    document_root = safe_join("/", settings.IMAGE_FILES_SUBDIRECTORY, pk)
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
