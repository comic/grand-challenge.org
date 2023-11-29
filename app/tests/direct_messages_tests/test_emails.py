from datetime import timedelta

import pytest
from django.utils.timezone import now

from grandchallenge.direct_messages.emails import get_users_to_email
from tests.direct_messages_tests.factories import DirectMessageFactory
from tests.factories import UserFactory


@pytest.mark.django_db
def test_users_to_be_email():
    users = UserFactory.create_batch(6)

    # Users 0 shouldn't be notified, no unread messages

    # Users 1 should be notified, 1 unread message
    DirectMessageFactory().unread_by.add(users[1])

    # Users 2 should be notified once, 2 unread messages from different users
    DirectMessageFactory().unread_by.add(users[2])
    DirectMessageFactory().unread_by.add(users[2])

    # Users 3 should be notified once, 2 unread messages from the same user
    sender = UserFactory()
    DirectMessageFactory(sender=sender).unread_by.add(users[3])
    DirectMessageFactory(sender=sender).unread_by.add(users[3])

    # Users 4 shouldn't be notified, no unread messages since last being emailed
    users[4].user_profile.unread_messages_email_last_sent_at = now()
    users[4].user_profile.save()
    dm = DirectMessageFactory()
    dm.created -= timedelta(hours=1)
    dm.save()
    dm.unread_by.add(users[4])

    # Users 5 should be notified, 1 unread message since being emailed
    users[5].user_profile.unread_messages_email_last_sent_at = now()
    users[5].user_profile.save()
    dm = DirectMessageFactory()
    dm.created -= timedelta(hours=1)
    dm.save()
    dm.unread_by.add(users[5])
    DirectMessageFactory().unread_by.add(users[5])

    users_to_email = get_users_to_email()

    assert [*users_to_email.order_by("pk")] == [
        users[1],
        users[2],
        users[3],
        users[5],
    ]
