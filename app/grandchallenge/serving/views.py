import posixpath

from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.utils._os import safe_join
from guardian.utils import get_anonymous_user
from knox.auth import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from grandchallenge.algorithms.models import AlgorithmImage, AlgorithmModel
from grandchallenge.cases.models import Image
from grandchallenge.challenges.models import ChallengeRequest
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.core.guardian import get_objects_for_user
from grandchallenge.core.storage import internal_protected_s3_storage
from grandchallenge.evaluation.models import Submission
from grandchallenge.serving.models import Download
from grandchallenge.workstations.models import Feedback


def protected_storage_redirect(*, name, **kwargs):
    _create_download(**kwargs)

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


def _create_download(
    *,
    creator,
    image=None,
    submission=None,
    component_interface_value=None,
    challenge_request=None,
    feedback=None,
    algorithm_model=None,
    algorithm_image=None,
):
    if creator.is_anonymous:
        creator = get_anonymous_user()

    kwargs = {"creator": creator}

    if image is not None:
        kwargs["image"] = image

    if submission is not None:
        kwargs["submission"] = submission

    if component_interface_value is not None:
        kwargs["component_interface_value"] = component_interface_value

    if challenge_request is not None:
        kwargs["challenge_request"] = challenge_request

    if feedback is not None:
        kwargs["feedback"] = feedback

    if algorithm_model is not None:
        kwargs["algorithm_model"] = algorithm_model

    if algorithm_image is not None:
        kwargs["algorithm_image"] = algorithm_image

    if len(kwargs) != 2:
        raise RuntimeError(
            "creator and only one other foreign key must be set"
        )

    Download.objects.create(**kwargs)


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
        return protected_storage_redirect(name=name, creator=user, image=image)

    raise PermissionDenied


def serve_submissions(request, *, submission_pk, **_):
    try:
        submission = Submission.objects.get(pk=submission_pk)
    except Submission.DoesNotExist:
        raise Http404("Submission not found.")

    if request.user.has_perm("view_submission", submission):
        return protected_storage_redirect(
            name=submission.predictions_file.name,
            creator=request.user,
            submission=submission,
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
            return protected_storage_redirect(
                name=civ.file.name, creator=user, component_interface_value=civ
            )

    raise PermissionDenied


def serve_structured_challenge_submission_form(
    request, *, challenge_request_pk, **_
):
    try:
        challenge_request = ChallengeRequest.objects.get(
            pk=challenge_request_pk
        )
    except ChallengeRequest.DoesNotExist:
        raise Http404("Challenge request not found.")

    if request.user.has_perm("view_challengerequest", challenge_request):
        return protected_storage_redirect(
            name=challenge_request.structured_challenge_submission_form.name,
            creator=request.user,
            challenge_request=challenge_request,
        )
    else:
        raise PermissionDenied


def serve_session_feedback_screenshot(request, *, feedback_pk, **_):
    try:
        feedback = Feedback.objects.get(pk=feedback_pk)
    except Feedback.DoesNotExist:
        raise Http404("Feedback not found.")

    if request.user.is_staff:
        return protected_storage_redirect(
            name=feedback.screenshot.name,
            creator=request.user,
            feedback=feedback,
        )
    else:
        raise PermissionDenied


def serve_algorithm_images(request, *, algorithmimage_pk, **_):
    try:
        image = AlgorithmImage.objects.get(pk=algorithmimage_pk)
    except AlgorithmImage.DoesNotExist:
        raise Http404("Algorithm image not found.")

    if request.user.has_perm("download_algorithmimage", image):
        return protected_storage_redirect(
            name=image.image.name,
            creator=request.user,
            algorithm_image=image,
        )

    raise PermissionDenied


def serve_algorithm_models(request, *, algorithmmodel_pk, **_):
    try:
        model = AlgorithmModel.objects.get(pk=algorithmmodel_pk)
    except AlgorithmModel.DoesNotExist:
        raise Http404("Algorithm model not found.")

    if request.user.has_perm("download_algorithmmodel", model):
        return protected_storage_redirect(
            name=model.model.name,
            creator=request.user,
            algorithm_model=model,
        )

    raise PermissionDenied
