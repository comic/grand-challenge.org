import pytest
from django.core import mail

from grandchallenge.discussion_forums.models import (
    ForumPost,
    ForumTopic,
    ForumTopicKindChoices,
    TopicReadRecord,
)
from grandchallenge.notifications.models import Notification
from grandchallenge.profiles.models import NotificationEmailOptions
from tests.discussion_forums_tests.factories import (
    ForumFactory,
    ForumPostFactory,
    ForumTopicFactory,
)
from tests.factories import UserFactory


@pytest.mark.django_db
def test_delete_only_post_also_deletes_topic():
    topic = ForumTopicFactory(post_count=2)

    assert topic.posts.count() == 2
    post1 = topic.posts.first()
    post2 = topic.posts.last()

    assert not post1.is_alone
    assert not post2.is_alone

    post2.delete()
    assert post1.is_alone

    post1.delete()
    assert ForumTopic.objects.count() == 0
    assert ForumPost.objects.count() == 0


@pytest.mark.django_db
def test_adding_post_updates_last_post_on_topic():
    topic = ForumTopicFactory(post_count=1)
    assert topic.posts.count() == 1
    post = topic.posts.first()
    assert topic.last_post == post
    assert topic.last_post_on == post.created

    post2 = ForumPostFactory(topic=topic)
    assert topic.last_post == post2
    assert topic.last_post_on == post2.created


@pytest.mark.django_db
def test_get_unread_topic_posts_for_user():
    topic = ForumTopicFactory(post_count=5)
    user = UserFactory()

    assert topic.get_unread_topic_posts_for_user(user=user).count() == 5

    TopicReadRecord.objects.create(user=user, topic=topic)

    assert topic.get_unread_topic_posts_for_user(user=user).count() == 0

    new_post = ForumPostFactory(topic=topic)

    assert topic.get_unread_topic_posts_for_user(user=user).count() == 1
    assert [new_post] == list(
        topic.get_unread_topic_posts_for_user(user=user).all()
    )


@pytest.mark.django_db
def test_forum_notifications_and_emails(
    django_capture_on_commit_callbacks, settings, mocker, caplog
):
    """Test that the create_forum_notifications task creates notifications, sends instant emails, and handles deleted objects during the task execution"""

    settings.LAMBDA_TASKS_EAGER = True

    forum = ForumFactory()
    participant = UserFactory()

    forum.linked_challenge.add_participant(participant)
    user_profile = participant.user_profile
    user_profile.notification_email_choice = NotificationEmailOptions.INSTANT
    user_profile.save()

    Notification.objects.all().delete()
    mail.outbox.clear()

    assert Notification.objects.count() == 0
    assert len(mail.outbox) == 0

    def create_announcement():
        caplog.clear()
        with caplog.at_level("ERROR", logger="lambda_tasks.logging"):
            with django_capture_on_commit_callbacks(execute=True):
                ForumTopicFactory(
                    forum=forum, kind=ForumTopicKindChoices.ANNOUNCE
                )

    create_announcement()
    # No errors were logged during the task execution
    assert not caplog.messages

    assert Notification.objects.count() == 2
    for notification in Notification.objects.all():
        assert notification.action_object == ForumTopic.objects.first()

    assert len(mail.outbox) == 1
    assert "You have 1 new notification" in mail.outbox[0].subject

    Notification.objects.all().delete()
    mail.outbox.clear()

    original_send = Notification.send

    def send_and_delete(*args, **kwargs):
        result = original_send(*args, **kwargs)
        # Simulate deletion during notification sending (i.e. during the task execution)
        ForumTopic.objects.filter(forum=forum).delete()
        return result

    mocker.patch.object(Notification, "send", side_effect=send_and_delete)

    create_announcement()

    # The task should have logged an error
    assert len(caplog.messages) == 1

    # Verify the error is about an object not existing (since we deleted it during the task)
    assert (
        f"{ForumTopic.__name__} matching query does not exist"
        in caplog.messages[0]
    )

    # Crucial: notifications and emails were not created because the task failed
    assert not Notification.objects.exists()
    assert len(mail.outbox) == 0
