import pytest

from grandchallenge.direct_messages.models import Conversation
from tests.direct_messages_tests.factories import (
    ConversationFactory,
    DirectMessageFactory,
    MuteFactory,
)
from tests.evaluation_tests.test_permissions import get_users_with_set_perms
from tests.factories import UserFactory


@pytest.mark.django_db
def test_unread_by_cleared_when_deleted():
    messages = DirectMessageFactory.create_batch(2)
    user = UserFactory()

    for message in messages:
        message.unread_by.add(user)

    messages[0].delete()

    for message in messages:
        message.refresh_from_db()

    assert messages[0].is_deleted is True
    assert {*messages[0].unread_by.all()} == set()
    assert messages[1].is_deleted is False
    assert {*messages[1].unread_by.all()} == {user}


@pytest.mark.django_db
def test_unread_by_cleared_when_marked_junk():
    messages = DirectMessageFactory.create_batch(2)
    user = UserFactory()

    for message in messages:
        message.unread_by.add(user)

    messages[0].is_reported_as_spam = True
    messages[0].save()

    for message in messages:
        message.refresh_from_db()

    assert messages[0].is_reported_as_spam is True
    assert {*messages[0].unread_by.all()} == set()
    assert messages[1].is_reported_as_spam is False
    assert {*messages[1].unread_by.all()} == {user}


@pytest.mark.django_db
def test_direct_message_permissions():
    user = UserFactory()
    message = DirectMessageFactory(sender=user)

    assert get_users_with_set_perms(message) == {
        user: {"delete_directmessage"}
    }


@pytest.mark.django_db
def test_mute_permissions():
    user = UserFactory()
    mute = MuteFactory(source=user)

    assert get_users_with_set_perms(mute) == {user: {"delete_mute"}}


@pytest.mark.django_db
def test_unread_by_updated_for_mute():
    sender, muter, other = UserFactory.create_batch(3)

    message = DirectMessageFactory(sender=sender)
    message.unread_by.add(muter, other)

    other_message = DirectMessageFactory()
    other_message.unread_by.add(muter, other)

    MuteFactory(source=muter, target=sender)

    assert {*message.unread_by.all()} == {other}
    assert {*other_message.unread_by.all()} == {muter, other}


@pytest.mark.django_db
def test_conversation_with_most_recent_message():
    conversation = ConversationFactory()
    user = UserFactory()

    ConversationFactory()  # No messages
    DirectMessageFactory(conversation=conversation)
    most_recent_message = DirectMessageFactory(conversation=conversation)

    queryset = Conversation.objects.order_by(
        "created"
    ).with_most_recent_message(user=user)

    assert (
        queryset[0].most_recent_message_created == most_recent_message.created
    )
    assert queryset[0].unread_message_count == 0
    assert queryset[0].unread_by_user is False
    assert queryset[1].most_recent_message_created is None
    assert queryset[1].unread_message_count == 0
    assert queryset[1].unread_by_user is False


@pytest.mark.django_db
def test_conversation_with_most_recent_message_unread():
    conversation = ConversationFactory()
    user = UserFactory()

    ConversationFactory()  # No messages
    DirectMessageFactory(conversation=conversation)
    message_1 = DirectMessageFactory(conversation=conversation)
    message_2 = DirectMessageFactory(conversation=conversation)
    message_3 = DirectMessageFactory()

    for message in {message_1, message_2, message_3}:
        message.unread_by.add(user)

    message_3.unread_by.add(UserFactory())

    queryset = Conversation.objects.order_by(
        "created"
    ).with_most_recent_message(user=user)

    assert queryset[0].most_recent_message_created == message_2.created
    assert queryset[0].unread_message_count == 2
    assert queryset[0].unread_by_user is True
    assert queryset[1].most_recent_message_created is None
    assert queryset[1].unread_message_count == 0
    assert queryset[1].unread_by_user is False
    assert queryset[2].most_recent_message_created == message_3.created
    assert queryset[2].unread_message_count == 1
    assert queryset[2].unread_by_user is True


@pytest.mark.django_db
def test_conversation_unread_by_user():
    conversation = ConversationFactory()
    user = UserFactory()

    messages = DirectMessageFactory.create_batch(3, conversation=conversation)

    messages[1].unread_by.add(user)
    messages[2].unread_by.add(UserFactory())

    other_message = DirectMessageFactory()
    other_message.unread_by.add(user)

    assert [
        message.unread_by_user
        for message in Conversation.objects.order_by("created")
        .with_unread_by_user(user=user)
        .first()
        .direct_messages.all()
    ] == [False, True, False]


@pytest.mark.django_db
def test_conversation_for_participants():
    u1, u2, u3, u4 = UserFactory.create_batch(4)

    c1, c2, c3, c4, c5, _ = ConversationFactory.create_batch(6)
    c1.participants.set([u1, u2])
    c2.participants.set([u1, u3])
    c3.participants.set([u2, u3])
    c4.participants.set([u1, u2, u3])
    c5.participants.set([u3, u4])

    assert (
        Conversation.objects.for_participants(participants=[u1, u2]).get()
        == c1
    )
