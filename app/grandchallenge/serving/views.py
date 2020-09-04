import posixpath

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.utils._os import safe_join
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from grandchallenge.cases.models import Image
from grandchallenge.core.storage import internal_protected_s3_storage
from grandchallenge.evaluation.models import Submission
from grandchallenge.serving.tasks import create_download


def protected_storage_redirect(*, name):
    # Get the storage with the internal redirect and auth. This will prepend
    # settings.PROTECTED_S3_STORAGE_KWARGS['endpoint_url'] to the url
    if not internal_protected_s3_storage.exists(name=name):
        raise Http404("File not found.")

    if settings.PROTECTED_S3_STORAGE_USE_CLOUDFRONT:
        response = HttpResponseRedirect(
            internal_protected_s3_storage.cloudfront_signed_url(name=name)
        )
    else:
        url = internal_protected_s3_storage.url(name=name)
        response = HttpResponseRedirect(url)

    return response


def serve_images(request, *, pk, path, pa="", pb=""):
    document_root = safe_join(
        f"/{settings.IMAGE_FILES_SUBDIRECTORY}", pa, pb, str(pk)
    )
    path = posixpath.normpath(path).lstrip("/")
    name = safe_join(document_root, path)

    try:
        image = Image.objects.get(pk=pk)
    except Image.DoesNotExist:
        raise Http404("Image not found.")

    try:
        user, _ = TokenAuthentication().authenticate(request)
    except (AuthenticationFailed, TypeError):
        user = request.user

    if user.has_perm("view_image", image):
        create_download.apply_async(
            kwargs={"creator_id": user.pk, "image_id": image.pk}
        )
        return protected_storage_redirect(name=name)

    raise PermissionDenied


def serve_submissions(request, *, submission_pk, **_):
    try:
        submission = Submission.objects.get(pk=submission_pk)
    except Submission.DoesNotExist:
        raise Http404("Submission not found.")

    if request.user.has_perm("view_submission", submission):
        create_download.apply_async(
            kwargs={
                "creator_id": request.user.pk,
                "submission_id": submission.pk,
            }
        )
        return protected_storage_redirect(
            name=submission.predictions_file.name
        )

    raise PermissionDenied
