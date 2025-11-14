from datetime import timedelta

import pytest
from django.core import mail
from django.utils.timezone import now

from grandchallenge.direct_messages.tasks import (
    get_new_senders,
    get_users_to_send_new_unread_direct_messages_email,
    send_new_unread_direct_messages_emails,
)
from grandchallenge.profiles.models import NotificationEmailOptions
from tests.direct_messages_tests.factories import (
    ConversationFactory,
    DirectMessageFactory,
)
from tests.factories import UserFactory
from tests.utils import get_view_for_user


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

    # Inactive user should not be notified
    DirectMessageFactory().unread_by.add(UserFactory(is_active=False))

    # Opt out user should not be notified
    opt_out_user = UserFactory()
    opt_out_user.user_profile.notification_email_choice = (
        NotificationEmailOptions.DISABLED
    )
    opt_out_user.user_profile.save()
    DirectMessageFactory().unread_by.add(opt_out_user)

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
        14
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


@pytest.mark.django_db
def test_instant_email_when_opted_in(client):
    u1, u2, u3, u4, u5 = UserFactory.create_batch(5)
    u1.user_profile.notification_email_choice = (
        NotificationEmailOptions.DISABLED
    )
    u2.user_profile.notification_email_choice = (
        NotificationEmailOptions.INSTANT
    )
    u3.user_profile.notification_email_choice = (
        NotificationEmailOptions.DAILY_SUMMARY
    )
    u4.is_active = False
    u1.user_profile.save()
    u2.user_profile.save()
    u3.user_profile.save()
    u4.save()

    conversation = ConversationFactory()
    conversation.participants.set([u1, u2, u3, u4, u5])

    get_view_for_user(
        client=client,
        viewname="direct_messages:direct-message-create",
        reverse_kwargs={"pk": conversation.pk},
        user=u5,
        method=client.post,
        data={"message": "🙈"},
    )

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [u2.email]
    for user in [u1, u2, u3, u4, u5]:
        user.user_profile.refresh_from_db()
    assert u2.user_profile.unread_messages_email_last_sent_at
    assert not u1.user_profile.unread_messages_email_last_sent_at
    assert not u3.user_profile.unread_messages_email_last_sent_at
    assert not u4.user_profile.unread_messages_email_last_sent_at
    assert not u5.user_profile.unread_messages_email_last_sent_at
