import pytest
from django.db import transaction

from grandchallenge.discussion_forums.models import ForumTopic
from grandchallenge.discussion_forums.tasks import create_forum_notifications
from grandchallenge.notifications.models import Notification
from tests.discussion_forums_tests.factories import ForumTopicFactory


@pytest.mark.django_db
def test_create_forum_notifications():
    """Postive test that the create_forum_notifications task creates notifications"""

    topic = ForumTopicFactory()
    assert Notification.objects.all().delete()

    assert Notification.objects.count() == 0

    # Call the task for the topic
    with transaction.atomic():
        create_forum_notifications(
            object_pk=str(topic.pk),
            app_label="discussion_forums",
            model_name="ForumTopic",
        )

    notification = Notification.objects.get()

    assert notification.action_object == topic


@pytest.mark.django_db
def test_create_forum_notifications_non_existing_object_late(mocker):
    """Test that the create_forum_notifications task handles the case where the object is deleted during the task execution."""
    topic = ForumTopicFactory()
    assert Notification.objects.all().delete()

    assert Notification.objects.count() == 0

    original_send = Notification.send

    def send_and_delete(*args, **kwargs):
        result = original_send(*args, **kwargs)
        topic.delete()  # Simulate deletion during notification sending (i.e. during the task execution)
        return result

    mocker.patch.object(Notification, "send", side_effect=send_and_delete)

    with pytest.raises(ForumTopic.DoesNotExist):
        with transaction.atomic():
            create_forum_notifications(
                object_pk=str(topic.pk),
                app_label="discussion_forums",
                model_name="ForumTopic",
            )

    assert Notification.objects.count() == 0
