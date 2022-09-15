import posixpath

from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, PermissionDenied
from django.db.models import F
from django.http import Http404, HttpResponseRedirect
from django.utils._os import safe_join
from knox.auth import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from grandchallenge.cases.models import Image
from grandchallenge.challenges.models import ChallengeRequest
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.core.guardian import get_objects_for_user
from grandchallenge.core.storage import internal_protected_s3_storage
from grandchallenge.evaluation.models import Submission
from grandchallenge.serving.models import Download
from grandchallenge.workstations.models import Feedback


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
        civ = ComponentInterfaceValue.objects.get(
            pk=component_interface_value_pk
        )
    except (MultipleObjectsReturned, ComponentInterfaceValue.DoesNotExist):
        raise Http404("No ComponentInterfaceValue found.")

    for perm, lookup in (
        ("algorithms.view_job", "outputs"),
        ("algorithms.view_job", "inputs"),
        ("evaluation.view_evaluation", "outputs"),
        ("evaluation.view_evaluation", "inputs"),
        ("archives.view_archiveitem", "values"),
        ("reader_studies.view_displayset", "values"),
    ):
        # Q | Q filters are very slow, this potentially does several db calls
        # but each is quite performant. Could be optimised later.
        if (
            get_objects_for_user(
                user=user,
                perms=perm,
            )
            .filter(**{lookup: civ})
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


def serve_session_feedback_screenshot(request, *, feedback_pk, **_):
    try:
        feedback = Feedback.objects.get(pk=feedback_pk)
    except Feedback.DoesNotExist:
        raise Http404("Feedback not found.")

    if request.user.is_staff:
        return protected_storage_redirect(name=feedback.screenshot.name)
    else:
        raise PermissionDenied
