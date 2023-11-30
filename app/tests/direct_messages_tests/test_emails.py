from datetime import timedelta

import pytest
from django.core import mail
from django.utils.timezone import now

from grandchallenge.direct_messages.emails import (
    get_new_senders,
    get_users_to_send_new_unread_direct_messages_email,
)
from grandchallenge.direct_messages.tasks import (
    send_new_unread_direct_messages_emails,
)
from tests.direct_messages_tests.factories import DirectMessageFactory
from tests.factories import UserFactory


@pytest.mark.django_db
def test_get_users_to_send_new_unread_direct_messages_email(
    django_assert_max_num_queries,
):
    users = UserFactory.create_batch(7)

    # Users 0 shouldn't be notified, no unread messages

    # Users 1 should be notified, 1 unread message
    dm1 = DirectMessageFactory()
    dm1.unread_by.add(users[1])

    # Users 2 should be notified once, 2 unread messages from different users
    dm2a = DirectMessageFactory()
    dm2a.unread_by.add(users[2])
    dm2b = DirectMessageFactory()
    dm2b.unread_by.add(users[2])

    # Users 3 should be notified once, 2 unread messages from the same user
    sender = UserFactory()
    DirectMessageFactory(sender=sender).unread_by.add(users[3])
    DirectMessageFactory(sender=sender).unread_by.add(users[3])

    # Users 4 shouldn't be notified, no unread messages since last being emailed
    users[4].user_profile.unread_messages_email_last_sent_at = now()
    users[4].user_profile.save()
    dm4 = DirectMessageFactory()
    dm4.created -= timedelta(hours=1)
    dm4.save()
    dm4.unread_by.add(users[4])

    # Users 5 should be notified, 1 unread message since being emailed
    users[5].user_profile.unread_messages_email_last_sent_at = now()
    users[5].user_profile.save()
    dm5a = DirectMessageFactory()
    dm5a.created -= timedelta(hours=1)
    dm5a.save()
    dm5a.unread_by.add(users[5])
    dm5b = DirectMessageFactory()
    dm5b.unread_by.add(users[5])

    # Users 6 should be notified, 1 unread message, here to test the number of queries
    dm6 = DirectMessageFactory()
    dm6.unread_by.add(users[6])

    with django_assert_max_num_queries(4):
        users_to_email = [
            {
                "user": user,
                "new_unread_message_count": user.new_unread_message_count,
                "new_senders": get_new_senders(user=user),
            }
            for user in get_users_to_send_new_unread_direct_messages_email().order_by(
                "pk"
            )
        ]

    assert users_to_email == [
        {
            "user": users[1],
            "new_unread_message_count": 1,
            "new_senders": [dm1.sender],
        },
        {
            "user": users[2],
            "new_unread_message_count": 2,
            "new_senders": [dm2a.sender, dm2b.sender],
        },
        {
            "user": users[3],
            "new_unread_message_count": 2,
            "new_senders": [sender],
        },
        {
            "user": users[5],
            "new_unread_message_count": 1,
            "new_senders": [dm5b.sender],
        },
        {
            "user": users[6],
            "new_unread_message_count": 1,
            "new_senders": [dm6.sender],
        },
    ]

    assert len(mail.outbox) == 0

    with django_assert_max_num_queries(
        10
    ):  # Extra queries to update the users profile
        send_new_unread_direct_messages_emails()

    assert len(mail.outbox) == 5
    assert {*get_users_to_send_new_unread_direct_messages_email()} == set()

    with django_assert_max_num_queries(2):
        send_new_unread_direct_messages_emails()

    assert len(mail.outbox) == 5

    assert [m.subject for m in mail.outbox] == [
        f"[testserver] You have 1 new message from {dm1.sender.first_name}",
        f"[testserver] You have 2 new messages from {dm2a.sender.first_name} and {dm2b.sender.first_name}",
        f"[testserver] You have 2 new messages from {sender.first_name}",
        f"[testserver] You have 1 new message from {dm5b.sender.first_name}",
        f"[testserver] You have 1 new message from {dm6.sender.first_name}",
    ]
