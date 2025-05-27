import pytest
from actstream.actions import follow, is_following
from actstream.models import Follow
from django.utils.html import format_html

from grandchallenge.discussion_forums.models import ForumTopicKindChoices
from grandchallenge.notifications.models import Notification
from grandchallenge.pages.models import Page
from grandchallenge.profiles.templatetags.profiles import user_profile_link
from tests.discussion_forums_tests.factories import (
    ForumFactory,
    ForumPostFactory,
    ForumTopicFactory,
)
from tests.factories import ChallengeFactory, UserFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "kind",
    (
        ForumTopicKindChoices.ANNOUNCE,
        ForumTopicKindChoices.STICKY,
        ForumTopicKindChoices.DEFAULT,
    ),
)
def test_notification_sent_on_new_topic(kind):
    u = UserFactory()
    f = ForumFactory()
    f.linked_challenge.add_participant(u)
    admin = f.linked_challenge.admins_group.user_set.get()

    # clear notifications
    Notification.objects.all().delete()
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
def test_notification_sent_on_new_post(kind):
    u = UserFactory()
    f = ForumFactory()
    f.linked_challenge.add_participant(u)
    admin = f.linked_challenge.admins_group.user_set.get()

    # clear notifications
    Notification.objects.all().delete()

    t = ForumTopicFactory(forum=f, creator=admin, kind=kind, post_count=1)
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
def test_follow_if_post_in_topic():
    u = UserFactory()
    f = ForumFactory()
    t = ForumTopicFactory(forum=f, post_count=1)
    ForumPostFactory(topic=t, creator=u)

    assert Follow.objects.is_following(user=u, instance=t)


@pytest.mark.django_db
def test_notification_created_for_target_followers_on_action_creation():
    u = UserFactory()
    f = ForumFactory()
    f.linked_challenge.add_participant(u)
    admin = f.linked_challenge.admins_group.user_set.get()

    # clear notifications
    Notification.objects.all().delete()

    # creating a post creates an action automatically
    _ = ForumTopicFactory(forum=f, creator=u)
    assert len(Notification.objects.all()) == 1

    notification = Notification.objects.get()
    # check that the poster did not receive a notification
    assert notification.user == admin
    assert notification.user != u


@pytest.mark.django_db
def test_follow_clean_up_after_topic_removal():
    u = UserFactory()
    f = ForumFactory()
    t1 = ForumTopicFactory(forum=f)
    t2 = ForumTopicFactory(forum=f)
    follow(u, t1, send_action=False)
    follow(u, t2, send_action=False)

    t1.delete()

    assert not is_following(u, t1)


@pytest.mark.django_db
def test_follow_clean_up_after_post_removal():
    u = UserFactory()
    f = ForumFactory()
    t = ForumTopicFactory(forum=f)
    p1 = ForumPostFactory(topic=t, creator=u)
    p2 = ForumPostFactory(topic=t, creator=u)

    follow(u, p1)
    follow(u, p2)

    p1.delete()

    assert not is_following(u, p1)


@pytest.mark.django_db
def test_follow_clean_up_after_forum_removal():
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
