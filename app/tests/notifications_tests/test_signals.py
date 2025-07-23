from datetime import timedelta

import pytest
from actstream import registry
from actstream.actions import follow, is_following
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.utils.html import format_html
from django.utils.timezone import now

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmPermissionRequest,
)
from grandchallenge.archives.models import Archive, ArchivePermissionRequest
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.challenges.models import Challenge
from grandchallenge.discussion_forums.models import (
    Forum,
    ForumPost,
    ForumTopic,
    ForumTopicKindChoices,
)
from grandchallenge.evaluation.models import Evaluation, Phase, Submission
from grandchallenge.notifications.models import Notification
from grandchallenge.pages.models import Page
from grandchallenge.participants.models import RegistrationRequest
from grandchallenge.profiles.templatetags.profiles import user_profile_link
from grandchallenge.reader_studies.models import (
    ReaderStudy,
    ReaderStudyPermissionRequest,
)
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmPermissionRequestFactory,
)
from tests.archives_tests.factories import (
    ArchiveFactory,
    ArchivePermissionRequestFactory,
)
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.discussion_forums_tests.factories import (
    ForumFactory,
    ForumPostFactory,
    ForumTopicFactory,
)
from tests.evaluation_tests.factories import (
    EvaluationFactory,
    PhaseFactory,
    SubmissionFactory,
)
from tests.factories import (
    ChallengeFactory,
    RegistrationRequestFactory,
    UserFactory,
)
from tests.notifications_tests.factories import NotificationFactory
from tests.reader_studies_tests.factories import (
    ReaderStudyFactory,
    ReaderStudyPermissionRequestFactory,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind",
    (
        ForumTopicKindChoices.ANNOUNCE,
        ForumTopicKindChoices.STICKY,
        ForumTopicKindChoices.DEFAULT,
    ),
)
def test_notification_sent_on_new_topic(
    kind, settings, django_capture_on_commit_callbacks
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    u = UserFactory()
    f = ForumFactory()
    f.linked_challenge.add_participant(u)
    admin = f.linked_challenge.admins_group.user_set.get()

    # clear notifications
    Notification.objects.all().delete()
    with django_capture_on_commit_callbacks(execute=True):
        t = ForumTopicFactory(
            forum=f,
            creator=admin,
            kind=kind,
        )

    notification = Notification.objects.get()
    topic_string = format_html('<a href="{}">{}</a>', t.get_absolute_url(), t)
    if kind == ForumTopicKindChoices.ANNOUNCE:
        assert notification.print_notification(user=u).startswith(
            f"{user_profile_link(admin)} announced {topic_string}"
        )
    else:
        assert notification.print_notification(user=u).startswith(
            f"{user_profile_link(admin)} posted {topic_string}"
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind",
    (
        ForumTopicKindChoices.ANNOUNCE,
        ForumTopicKindChoices.STICKY,
        ForumTopicKindChoices.DEFAULT,
    ),
)
def test_notification_sent_on_new_post(
    kind, settings, django_capture_on_commit_callbacks
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    u = UserFactory()
    f = ForumFactory()
    f.linked_challenge.add_participant(u)
    admin = f.linked_challenge.admins_group.user_set.get()

    # clear notifications
    Notification.objects.all().delete()

    with django_capture_on_commit_callbacks(execute=True):
        t = ForumTopicFactory(forum=f, creator=admin, kind=kind, post_count=0)
        ForumPostFactory(topic=t, creator=u)

    notifications = Notification.objects.all()
    topic_string = format_html('<a href="{}">{}</a>', t.get_absolute_url(), t)
    forum_string = format_html('<a href="{}">{}</a>', f.get_absolute_url(), f)
    assert len(notifications) == 2
    assert (
        notifications[1]
        .print_notification(user=admin)
        .startswith(f"{user_profile_link(u)} replied to {topic_string}")
    )

    if kind == ForumTopicKindChoices.ANNOUNCE:
        assert (
            notifications[0]
            .print_notification(user=u)
            .startswith(
                f"{user_profile_link(admin)} announced {topic_string} in {forum_string}"
            )
        )
    else:
        assert (
            notifications[0]
            .print_notification(user=2)
            .startswith(
                f"{user_profile_link(admin)} posted {topic_string} in {forum_string}"
            )
        )


@pytest.mark.django_db
def test_follow_if_post_in_topic(settings, django_capture_on_commit_callbacks):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    u = UserFactory()

    with django_capture_on_commit_callbacks(execute=True):
        f = ForumFactory()
        t = ForumTopicFactory(forum=f, post_count=0)
    assert not is_following(user=u, obj=t)

    with django_capture_on_commit_callbacks(execute=True):
        ForumPostFactory(topic=t, creator=u)
    assert is_following(user=u, obj=t)


@pytest.mark.django_db
def test_notification_created_for_target_followers_on_action_creation(
    settings,
    django_capture_on_commit_callbacks,
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    u = UserFactory()
    f = ForumFactory()
    f.linked_challenge.add_participant(u)
    admin = f.linked_challenge.admins_group.user_set.get()

    # clear notifications
    Notification.objects.all().delete()

    # creating a post creates an action automatically
    with django_capture_on_commit_callbacks(execute=True):
        _ = ForumTopicFactory(forum=f, creator=u)
    assert len(Notification.objects.all()) == 1

    notification = Notification.objects.get()
    # check that the poster did not receive a notification
    assert notification.user == admin
    assert notification.user != u


MODEL_TO_FACTORY = {
    AlgorithmPermissionRequest: (AlgorithmPermissionRequestFactory, {}),
    ReaderStudyPermissionRequest: (ReaderStudyPermissionRequestFactory, {}),
    ArchivePermissionRequest: (ArchivePermissionRequestFactory, {}),
    Archive: (ArchiveFactory, {}),
    Algorithm: (AlgorithmFactory, {}),
    ReaderStudy: (ReaderStudyFactory, {}),
    ForumTopic: (ForumTopicFactory, {}),
    ForumPost: (ForumPostFactory, {}),
    RegistrationRequest: (RegistrationRequestFactory, {}),
    Evaluation: (EvaluationFactory, {"time_limit": 10}),
    Phase: (PhaseFactory, {}),
    Submission: (SubmissionFactory, {}),
    RawImageUploadSession: (RawImageUploadSessionFactory, {}),
    User: (UserFactory, {}),
}


def test_all_registered_models_have_factory_coverage():
    """Ensure all models registered with actstream have corresponding factories for the below test."""
    registered_models = set(registry.registry.keys())
    # Exclude Challenge and Forum models since we have seperate tests for those
    registered_models.discard(Challenge)
    registered_models.discard(Forum)

    factory_covered_models = set(MODEL_TO_FACTORY.keys())

    missing_factories = registered_models - factory_covered_models
    extra_factories = factory_covered_models - registered_models

    assert (
        not missing_factories
    ), f"These registered models are missing factory coverage: {missing_factories}"
    assert (
        not extra_factories
    ), f"These factories are for models not in registry: {extra_factories}"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "factory, extra_factory_kwargs",
    list(MODEL_TO_FACTORY.values()),
    ids=[model._meta.label for model in MODEL_TO_FACTORY.keys()],
)
def test_follow_clean_up_after_object_removal(factory, extra_factory_kwargs):
    # IMPORTANT:
    # if a new model needs to be added to clean_up_follows to satisfy this test,
    # this model should also be added to clean_up_notifications !
    u = UserFactory()
    o1, o2 = factory.create_batch(2, **extra_factory_kwargs)
    follow(u, o1, send_action=False)
    follow(u, o2, send_action=False)

    o1.delete()

    assert not is_following(u, o1)


@pytest.mark.django_db
def test_follow_clean_up_after_forum_removal():
    # test seperately because test logic differs slightly
    u = UserFactory()
    f1 = ForumFactory()
    f2 = ForumFactory()
    follow(u, f1, send_action=False)
    follow(u, f2, send_action=False)

    Page.objects.all().delete()
    f1.linked_challenge.delete()
    f1.delete()

    assert not is_following(u, f1)


@pytest.mark.django_db
def test_follow_clean_up_after_challenge_removal():
    # test seperately because test logic differs slightly
    u = UserFactory()
    c1 = ChallengeFactory()
    c2 = ChallengeFactory()
    follow(u, c1, send_action=False)
    follow(u, c2, send_action=False)

    Page.objects.all().delete()
    c1.delete()

    assert not is_following(u, c1)


@pytest.mark.django_db
def test_notification_for_new_admin_only():
    user = UserFactory()
    admin = UserFactory()
    challenge = ChallengeFactory(creator=admin)

    # clear existing notifications for easier testing below
    Notification.objects.all().delete()

    # add user as admin to challenge
    challenge.add_admin(user)

    assert Notification.objects.count() == 1
    assert Notification.objects.get().user == user
    assert Notification.objects.get().user != admin


@pytest.mark.django_db
@pytest.mark.parametrize(
    "object_reference, kind, actor, target, action_object, action_object_extra_kwargs",
    [
        [
            "target",
            Notification.Type.REQUEST_UPDATE,
            None,
            AlgorithmPermissionRequestFactory,
            None,
            {},
        ],
        [
            "target",
            Notification.Type.REQUEST_UPDATE,
            None,
            ReaderStudyPermissionRequestFactory,
            None,
            {},
        ],
        [
            "target",
            Notification.Type.REQUEST_UPDATE,
            None,
            ArchivePermissionRequestFactory,
            None,
            {},
        ],
        [
            "target",
            Notification.Type.ACCESS_REQUEST,
            UserFactory,
            ArchiveFactory,
            None,
            {},
        ],
        [
            "target",
            Notification.Type.ACCESS_REQUEST,
            UserFactory,
            AlgorithmFactory,
            None,
            {},
        ],
        [
            "target",
            Notification.Type.ACCESS_REQUEST,
            UserFactory,
            ReaderStudyFactory,
            None,
            {},
        ],
        [
            "target",
            Notification.Type.FORUM_POST_REPLY,
            UserFactory,
            ForumTopicFactory,
            None,
            {},
        ],
        [
            "action_object",
            Notification.Type.EVALUATION_STATUS,
            UserFactory,
            PhaseFactory,
            EvaluationFactory,
            {"time_limit": 10},
        ],
        [
            "action_object",
            Notification.Type.MISSING_METHOD,
            UserFactory,
            PhaseFactory,
            SubmissionFactory,
            {},
        ],
        [
            "target",
            Notification.Type.EVALUATION_STATUS,
            UserFactory,
            PhaseFactory,
            EvaluationFactory,
            {"time_limit": 10},
        ],
        [
            "action_object",
            Notification.Type.IMAGE_IMPORT_STATUS,
            None,
            None,
            RawImageUploadSessionFactory,
            {},
        ],
        [
            "actor",
            Notification.Type.CIV_VALIDATION,
            UserFactory,
            None,
            None,
            {},
        ],
    ],
)
def test_notification_clean_up_after_object_removal(
    object_reference,
    kind,
    actor,
    target,
    action_object,
    action_object_extra_kwargs,
):
    u = UserFactory()

    notification = NotificationFactory(
        user=u,
        type=kind,
        actor=actor() if actor else None,
        target=target() if target else None,
        message="foo",
        action_object=(
            action_object(**action_object_extra_kwargs)
            if action_object
            else None
        ),
    )

    getattr(notification, object_reference).delete()

    assert not Notification.objects.filter(pk=notification.pk).exists()


@pytest.mark.django_db
def test_forum_post_notification_clean_up_after_forum_removal():
    u = UserFactory()
    forum = ForumFactory()

    notification = NotificationFactory(
        user=u,
        type=Notification.Type.FORUM_POST,
        actor=UserFactory(),
        target=forum,
        message="foo",
        action_object=ForumTopicFactory(),
    )

    Page.objects.all().delete()
    forum.linked_challenge.delete()
    forum.delete()

    assert not Notification.objects.filter(pk=notification.pk).exists()


@pytest.mark.django_db
def test_permission_denied_when_posting(settings):
    settings.FORUMS_MIN_ACCOUNT_AGE_DAYS = 1

    f = ForumFactory()
    old_user = UserFactory()
    old_user.date_joined = now() - timedelta(days=2)
    old_user.save()
    topic = ForumTopicFactory(forum=f, creator=old_user)

    user = UserFactory()

    with pytest.raises(PermissionDenied):
        ForumTopicFactory(forum=f, creator=user)

    with pytest.raises(PermissionDenied):
        ForumPostFactory(creator=user, topic=topic)

    user.date_joined = now() - timedelta(days=2)
    user.save()

    ForumTopicFactory(forum=f, creator=user)
    ForumPostFactory(creator=user, topic=topic)
