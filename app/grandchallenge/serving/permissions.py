from grandchallenge.cases.models import Image
from grandchallenge.datasets.models import AnnotationSet, ImageSet
from grandchallenge.evaluation.models import Submission


def user_can_download_imageset(*, user, imageset: ImageSet) -> bool:
    challenge = imageset.challenge
    return challenge.is_participant(user) or challenge.is_admin(user)


def user_can_download_annotationset(
    *, user, annotationset: AnnotationSet
) -> bool:
    challenge = annotationset.base.challenge
    if (
        annotationset.base.phase == ImageSet.TESTING
        and annotationset.kind == AnnotationSet.GROUNDTRUTH
    ):
        return challenge.is_admin(user)
    else:
        return challenge.is_participant(user) or challenge.is_admin(user)


def user_can_download_image(*, user, image: Image) -> bool:
    if user.has_perm("view_image", image):
        return True

    imagesets = image.imagesets.all().select_related("challenge")

    for imageset in imagesets:
        if user_can_download_imageset(user=user, imageset=imageset):
            return True

    annotationsets = image.annotationsets.all().select_related(
        "base__challenge"
    )

    for annotationset in annotationsets:
        if user_can_download_annotationset(
            user=user, annotationset=annotationset
        ):
            return True

    return False


def user_can_download_submission(*, user, submission: Submission) -> bool:
    return submission.challenge.is_admin(user=user)
