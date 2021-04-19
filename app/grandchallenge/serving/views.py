import posixpath

from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, PermissionDenied
from django.db.models import Q
from django.db.transaction import on_commit
from django.http import Http404, HttpResponseRedirect
from django.utils._os import safe_join
from guardian.shortcuts import get_objects_for_user
from knox.auth import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from grandchallenge.cases.models import Image
from grandchallenge.components.models import ComponentInterfaceValue
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
        on_commit(
            lambda: create_download.apply_async(
                kwargs={"creator_id": user.pk, "image_id": image.pk}
            )
        )
        return protected_storage_redirect(name=name)

    raise PermissionDenied


def serve_submissions(request, *, submission_pk, **_):
    try:
        submission = Submission.objects.get(pk=submission_pk)
    except Submission.DoesNotExist:
        raise Http404("Submission not found.")

    if request.user.has_perm("view_submission", submission):
        on_commit(
            lambda: create_download.apply_async(
                kwargs={
                    "creator_id": request.user.pk,
                    "submission_id": submission.pk,
                }
            )
        )
        return protected_storage_redirect(
            name=submission.predictions_file.name
        )

    raise PermissionDenied


def serve_component_interface_value(
    request, *, component_interface_value_pk, **_
):
    try:
        user, _ = TokenAuthentication().authenticate(request)
    except (AuthenticationFailed, TypeError):
        user = request.user

    try:
        # output should only be connected to a single job; throw error if not?
        civ = ComponentInterfaceValue.objects.get(
            pk=component_interface_value_pk
        )
    except (MultipleObjectsReturned, ComponentInterfaceValue.DoesNotExist):
        raise Http404("No ComponentInterfaceValue found.")

    if (
        get_objects_for_user(user=user, perms="algorithms.view_job")
        .filter(
            Q(outputs__pk=component_interface_value_pk)
            | Q(inputs__pk=component_interface_value_pk)
        )
        .exists()
    ):
        return protected_storage_redirect(name=civ.file.name)

    raise PermissionDenied
