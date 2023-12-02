import pytest
from guardian.utils import get_anonymous_user

from grandchallenge.direct_messages.models import Conversation
from tests.direct_messages_tests.factories import (
    ConversationFactory,
    DirectMessageFactory,
)
from tests.evaluation_tests.test_permissions import get_users_with_set_perms
from tests.factories import UserFactory


@pytest.mark.django_db
@pytest.mark.parametrize("reverse", [True, False])
def test_conversation_participants_permissions_signal(reverse):
    c1, c2 = ConversationFactory.create_batch(2)
    u1, u2, u3, u4 = UserFactory.create_batch(4)

    if reverse:
        for user in [u1, u2, u3, u4]:
            user.conversations.add(c1, c2)
        for user in [u3, u4]:
            user.conversations.remove(c1, c2)
        for user in [u1, u2]:
            user.conversations.remove(c2)
    else:
        c1.participants.add(u1, u2, u3, u4)
        c1.participants.remove(u3, u4)

    assert get_users_with_set_perms(c1) == {
        u1: {
            "view_conversation",
            "create_conversation_direct_message",
            "mark_conversation_read",
            "mark_conversation_message_as_spam",
        },
        u2: {
            "view_conversation",
            "create_conversation_direct_message",
            "mark_conversation_read",
            "mark_conversation_message_as_spam",
        },
    }
    assert get_users_with_set_perms(c2) == {}

    # Test clearing
    if reverse:
        u1.conversations.clear()
        u2.conversations.clear()
    else:
        c1.participants.clear()

    assert get_users_with_set_perms(c1) == {}
    assert get_users_with_set_perms(c2) == {}


@pytest.mark.django_db
def test_anon_not_participant():
    conversation = ConversationFactory()

    with pytest.raises(RuntimeError) as e:
        conversation.participants.add(get_anonymous_user())

    assert str(e.value) == "The Anonymous User cannot be added to this group"


@pytest.mark.django_db
def test_unread_removal():
    users = UserFactory.create_batch(2)

    for _ in range(2):
        conversation = ConversationFactory()
        conversation.participants.set(users)

        message = DirectMessageFactory(
            conversation=conversation, sender=users[0]
        )
        message.unread_by.set(users)

    conversation.participants.remove(users[1])

    conversations = Conversation.objects.order_by(
        "created"
    ).with_most_recent_message(user=users[1])

    assert conversations[0].unread_by_user is True
    assert conversations[1].unread_by_user is False

    conversations = Conversation.objects.order_by(
        "created"
    ).with_most_recent_message(user=users[0])

    assert conversations[0].unread_by_user is True
    assert conversations[1].unread_by_user is True
