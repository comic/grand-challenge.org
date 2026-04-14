import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save
from django.utils import timezone

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmPermissionRequest,
)
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.challenges.models import Challenge
from grandchallenge.discussion_forums.models import (
    Forum,
    ForumPost,
    ForumTopic,
)
from grandchallenge.evaluation.models import Evaluation, Phase, Submission
from grandchallenge.notifications.models import (
    Notification,
    NotificationTypeChoices,
)
from grandchallenge.notifications.signals import disallow_spam
from grandchallenge.participants.models import RegistrationRequest


def run():
    """Creates notifications covering all print_notification branches."""
    print("🔔 Creating notification fixtures 🔔")

    if not settings.DEBUG:
        raise RuntimeError(
            "Skipping this command, server is not in DEBUG mode."
        )

    demo, demop = _get_users()
    challenge = _get_challenge()
    algorithm = _get_algorithm()

    # Clean up any previously created fixture notifications so the
    # script is idempotent.
    Notification.objects.filter(user__username__in=["demo", "demop"]).delete()

    notifications = []
    notifications += _create_forum_notifications(demo, demop)
    notifications += _create_access_request_notifications(
        demo, demop, challenge, algorithm
    )
    notifications += _create_request_update_notifications(
        demop, challenge, algorithm
    )
    notifications += _create_admin_notifications(demo, challenge)
    notifications += _create_evaluation_notifications(demo, demop, challenge)
    notifications += _create_job_notifications(demo, demop, algorithm)
    notifications += _create_import_and_validation_notifications(demo)

    # Mark some as read for visual variety
    for n in random.sample(notifications, k=min(4, len(notifications))):
        Notification.objects.filter(pk=n.pk).update(read=True)

    print(
        f"✨ Created {len(notifications)} notifications for users "
        f"demo and demop ✨"
    )


def _get_users():
    user_model = get_user_model()
    try:
        demo = user_model.objects.get(username="demo")
        demop = user_model.objects.get(username="demop")
    except user_model.DoesNotExist:
        raise RuntimeError(
            "Run development_fixtures first to create the required users."
        )
    return demo, demop


def _get_challenge():
    challenge = Challenge.objects.filter(short_name="demo").first()
    if challenge is None:
        raise RuntimeError(
            "Run development_fixtures first to create the demo challenge."
        )
    return challenge


def _get_algorithm():
    algorithm = Algorithm.objects.first()
    if algorithm is None:
        raise RuntimeError(
            "Run development_fixtures first to create an algorithm."
        )
    return algorithm


def _create_forum_notifications(demo, demop):
    notifications = []
    forum = Forum.objects.first()
    if not forum:
        print("  ⚠ Skipping FORUM_POST — no forum found")
        return notifications

    topic = ForumTopic.objects.filter(forum=forum).first()
    if topic is None:
        pre_save.disconnect(disallow_spam, sender=ForumTopic)
        try:
            topic = ForumTopic.objects.create(
                forum=forum,
                creator=demop,
                subject="Example discussion topic",
            )
        finally:
            pre_save.connect(disallow_spam, sender=ForumTopic)

    post = ForumPost.objects.filter(topic=topic).first()
    if post is None:
        pre_save.disconnect(disallow_spam, sender=ForumPost)
        pre_save.disconnect(disallow_spam, sender=ForumTopic)
        try:
            post = ForumPost.objects.create(
                topic=topic,
                creator=demop,
                content="This is an example post.",
            )
        finally:
            pre_save.connect(disallow_spam, sender=ForumPost)
            pre_save.connect(disallow_spam, sender=ForumTopic)

    notifications.append(
        _create(
            user=demo,
            kind=NotificationTypeChoices.FORUM_POST,
            actor=demop,
            message="posted",
            action_object=topic,
            target=forum,
            minutes_ago=5,
        )
    )
    notifications.append(
        _create(
            user=demo,
            kind=NotificationTypeChoices.FORUM_POST_REPLY,
            actor=demop,
            message="replied to",
            target=topic,
            minutes_ago=12,
        )
    )
    return notifications


def _create_access_request_notifications(demo, demop, challenge, algorithm):
    return [
        _create(
            user=demo,
            kind=NotificationTypeChoices.ACCESS_REQUEST,
            actor=demop,
            message="requested access to",
            target=challenge,
            minutes_ago=60 * 3,
        ),
        _create(
            user=demo,
            kind=NotificationTypeChoices.ACCESS_REQUEST,
            actor=demop,
            message="requested access to",
            target=algorithm,
            minutes_ago=60 * 24,
        ),
    ]


def _create_request_update_notifications(demop, challenge, algorithm):
    reg_request = RegistrationRequest.objects.filter(
        challenge=challenge,
    ).first()
    if reg_request is None:
        reg_request = RegistrationRequest(
            user=demop,
            challenge=challenge,
            status=RegistrationRequest.ACCEPTED,
        )
        RegistrationRequest.objects.bulk_create([reg_request])

    alg_perm = AlgorithmPermissionRequest.objects.filter(
        algorithm=algorithm,
        user=demop,
    ).first()
    if alg_perm is None:
        alg_perm = AlgorithmPermissionRequest(
            algorithm=algorithm,
            user=demop,
            status=AlgorithmPermissionRequest.REJECTED,
        )
        AlgorithmPermissionRequest.objects.bulk_create([alg_perm])

    return [
        _create(
            user=demop,
            kind=NotificationTypeChoices.REQUEST_UPDATE,
            message="was accepted",
            target=reg_request,
            minutes_ago=60 * 24 * 14,
        ),
        _create(
            user=demop,
            kind=NotificationTypeChoices.REQUEST_UPDATE,
            message="was rejected",
            target=alg_perm,
            minutes_ago=60 * 24 * 2,
        ),
    ]


def _create_admin_notifications(demo, challenge):
    return [
        _create(
            user=demo,
            kind=NotificationTypeChoices.NEW_ADMIN,
            message="added as an admin to",
            target=challenge,
            action_object=demo,
            minutes_ago=60 * 24 * 7,
        ),
    ]


def _create_evaluation_notifications(demo, demop, challenge):
    notifications = []
    phase = Phase.objects.filter(challenge=challenge).first()
    submission = Submission.objects.filter(phase=phase).first()
    evaluation = Evaluation.objects.filter(submission=submission).first()

    if not evaluation:
        print(
            "  ⚠ Skipping EVALUATION_STATUS / MISSING_METHOD"
            " — no evaluation found"
        )
        return notifications

    creator = evaluation.submission.creator
    notifications.append(
        _create(
            user=creator,
            kind=NotificationTypeChoices.EVALUATION_STATUS,
            actor=creator,
            message="failed",
            action_object=evaluation,
            target=phase,
            minutes_ago=45,
        )
    )
    notifications.append(
        _create(
            user=demo,
            kind=NotificationTypeChoices.EVALUATION_STATUS,
            actor=demop,
            message="failed",
            action_object=evaluation,
            target=phase,
            minutes_ago=60 * 2,
        )
    )
    notifications.append(
        _create(
            user=demo,
            kind=NotificationTypeChoices.EVALUATION_STATUS,
            actor=demop,
            message="succeeded",
            action_object=evaluation,
            target=phase,
            minutes_ago=60 * 5,
        )
    )
    notifications.append(
        _create(
            user=demo,
            kind=NotificationTypeChoices.MISSING_METHOD,
            actor=demop,
            action_object=submission,
            target=phase,
            minutes_ago=60 * 24 * 3,
        )
    )
    return notifications


def _create_job_notifications(demo, demop, algorithm):
    return [
        _create(
            user=demo,
            kind=NotificationTypeChoices.JOB_STATUS,
            actor=demop,
            message=(
                "Unfortunately one of the jobs for algorithm "
                f"{algorithm.title} failed with an error"
            ),
            description="/",
            minutes_ago=30,
        ),
        _create(
            user=demo,
            kind=NotificationTypeChoices.JOB_STATUS,
            actor=demo,
            message=(
                f"One of the jobs for algorithm {algorithm.title} succeeded"
            ),
            description="/",
            minutes_ago=60 * 48,
        ),
    ]


def _create_import_and_validation_notifications(demo):
    upload_session = RawImageUploadSession.objects.first()
    if upload_session is None:
        upload_session = RawImageUploadSession.objects.create(creator=demo)

    return [
        _create(
            user=demo,
            kind=NotificationTypeChoices.IMAGE_IMPORT_STATUS,
            action_object=upload_session,
            description=(
                "Image validation for socket Generic Overlay failed "
                "with error: 1 file could not be imported."
            ),
            minutes_ago=60 * 24 * 30,
        ),
        _create(
            user=demo,
            kind=NotificationTypeChoices.FILE_COPY_STATUS,
            actor=demo,
            description=(
                "Validation for socket Points of interest failed: "
                "The file could not be decoded"
            ),
            context_class="danger",
            minutes_ago=10,
        ),
        _create(
            user=demo,
            kind=NotificationTypeChoices.CIV_VALIDATION,
            actor=demo,
            description=(
                "Component interface value validation failed: "
                "Expected a JSON file but received a PNG."
            ),
            context_class="warning",
            minutes_ago=60 * 24 * 60,
        ),
        _create(
            user=demo,
            kind=NotificationTypeChoices.CIV_VALIDATION,
            actor=demo,
            description=(
                "Component interface value validation failed for "
                "interface 'Generic Overlay' (slug: generic-overlay):"
                " The uploaded file could not be decoded. Please "
                "ensure that the file is a valid image in one of the"
                " supported formats (MHA, MHD, TIFF, or NIFTI). The"
                " following errors were encountered during "
                "validation: (1) The file header could not be parsed"
                " — this usually indicates a corrupted or truncated "
                "upload. (2) The pixel data dimensions (expected "
                "512×512×3) do not match the declared shape in the "
                "metadata. (3) The voxel spacing values are missing "
                "or invalid, which is required for spatial "
                "normalization. Please re-export the file from your "
                "source application and try uploading again. If the "
                "problem persists, contact support with the upload "
                "session ID and the original file for further "
                "investigation."
            ),
            context_class="warning",
            minutes_ago=60 * 6,
        ),
    ]


def _create(
    *,
    user,
    kind,
    actor=None,
    action_object=None,
    target=None,
    message=None,
    description=None,
    context_class=None,
    minutes_ago=0,
):
    """Create a notification and backdate it."""
    n = Notification.objects.create(
        user=user,
        type=kind,
        actor=actor,
        action_object=action_object,
        target=target,
        message=message,
        description=description,
        context_class=context_class,
    )
    if minutes_ago:
        Notification.objects.filter(pk=n.pk).update(
            created=timezone.now() - timedelta(minutes=minutes_ago)
        )
    return n
