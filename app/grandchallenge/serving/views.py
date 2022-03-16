import posixpath

from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, PermissionDenied
from django.db.models import F, Q
from django.http import Http404, HttpResponseRedirect
from django.utils._os import safe_join
from guardian.shortcuts import get_objects_for_user
from knox.auth import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from grandchallenge.cases.models import Image
from grandchallenge.challenges.models import ChallengeRequest
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.core.storage import internal_protected_s3_storage
from grandchallenge.evaluation.models import Submission
from grandchallenge.serving.models import Download


def protected_storage_redirect(*, name):
    # Get the storage with the internal redirect and auth. This will prepend
    # settings.AWS_S3_ENDPOINT_URL to the url
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
        _create_download(creator_id=user.pk, image_id=image.pk)
        return protected_storage_redirect(name=name)

    raise PermissionDenied


def serve_submissions(request, *, submission_pk, **_):
    try:
        submission = Submission.objects.get(pk=submission_pk)
    except Submission.DoesNotExist:
        raise Http404("Submission not found.")

    if request.user.has_perm("view_submission", submission):
        _create_download(
            creator_id=request.user.pk, submission_id=submission.pk
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
        get_objects_for_user(
            user=user, perms="algorithms.view_job", accept_global_perms=False
        )
        .filter(
            Q(outputs__pk=component_interface_value_pk)
            | Q(inputs__pk=component_interface_value_pk)
        )
        .exists()
    ):
        return protected_storage_redirect(name=civ.file.name)
    elif (
        get_objects_for_user(
            user=user,
            perms="evaluation.view_evaluation",
            accept_global_perms=False,
        )
        .filter(
            Q(outputs__pk=component_interface_value_pk)
            | Q(inputs__pk=component_interface_value_pk)
        )
        .exists()
    ):
        return protected_storage_redirect(name=civ.file.name)

    raise PermissionDenied


def _create_download(*, creator_id, image_id=None, submission_id=None):
    kwargs = {"creator_id": creator_id}

    if image_id is not None:
        kwargs["image_id"] = image_id

    if submission_id is not None:
        kwargs["submission_id"] = submission_id

    n_updated = Download.objects.filter(**kwargs).update(count=F("count") + 1)

    if n_updated == 0:
        Download.objects.create(**kwargs)


def serve_structured_challenge_submission_form(
    request, *, challenge_request_pk, **_
):
    try:
        challenge_request = ChallengeRequest.objects.get(
            pk=challenge_request_pk
        )
    except ChallengeRequest.DoesNotExist:
        raise Http404("Challenge request not found.")

    if request.user.has_perm("challenges.view_challengerequest"):
        return protected_storage_redirect(
            name=challenge_request.structured_challenge_submission_form.name
        )
    else:
        raise PermissionDenied
