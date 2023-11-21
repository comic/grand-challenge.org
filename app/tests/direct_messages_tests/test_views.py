import pytest
from guardian.utils import get_anonymous_user

from grandchallenge.direct_messages.models import Conversation, Mute
from tests.direct_messages_tests.factories import (
    ConversationFactory,
    DirectMessageFactory,
    MuteFactory,
)
from tests.factories import ChallengeFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_conversation_create_permissions(client, settings):
    def try_create_conversation(creator, target):
        return get_view_for_user(
            client=client,
            viewname="direct_messages:conversation-create",
            reverse_kwargs={"username": target.username},
            user=creator,
        )

    admin, participant = UserFactory.create_batch(2)
    challenge = ChallengeFactory()

    # Normal users cannot create conversations with each other
    response = try_create_conversation(creator=admin, target=participant)
    assert response.status_code == 403

    # Challenge admins cannot message anyone
    challenge.add_admin(user=admin)
    response = try_create_conversation(creator=admin, target=participant)
    assert response.status_code == 403

    # Only admins should be able to contact participants
    challenge.add_participant(user=participant)
    response = try_create_conversation(creator=admin, target=participant)
    assert response.status_code == 200

    # One way, participants should not be able to initiate conversations
    response = try_create_conversation(creator=participant, target=admin)
    assert response.status_code == 403

    # Anonymous user shouldn't be messaged
    anon = get_anonymous_user()
    challenge.participants_group.user_set.add(anon)
    response = try_create_conversation(creator=admin, target=anon)
    assert response.status_code == 403

    # Anonymous user shouldn't be able to create messages
    challenge.admins_group.user_set.add(anon)
    response = try_create_conversation(creator=anon, target=participant)
    assert response.status_code == 302
    assert response.url.startswith(settings.LOGIN_URL)


@pytest.mark.django_db
def test_existing_converstion_redirect(client):
    admin, participant = UserFactory.create_batch(2)
    challenge = ChallengeFactory()
    challenge.add_admin(user=admin)
    challenge.add_participant(user=participant)

    conversation = ConversationFactory()
    conversation.participants.set([admin, participant])

    response = get_view_for_user(
        client=client,
        viewname="direct_messages:conversation-create",
        reverse_kwargs={"username": participant.username},
        user=admin,
        method=client.post,
    )
    assert response.status_code == 302
    assert (
        response.url
        == f"https://testserver/messages/?conversation={conversation.pk}"
    )


@pytest.mark.django_db
def test_new_conversation_redirect(client):
    admin, participant = UserFactory.create_batch(2)
    challenge = ChallengeFactory()
    challenge.add_admin(user=admin)
    challenge.add_participant(user=participant)

    response = get_view_for_user(
        client=client,
        viewname="direct_messages:conversation-create",
        reverse_kwargs={"username": participant.username},
        user=admin,
        method=client.post,
    )
    assert response.status_code == 302

    conversation = Conversation.objects.get()

    assert (
        response.url
        == f"https://testserver/messages/?conversation={conversation.pk}"
    )


@pytest.mark.django_db
def test_direct_message_unread(client):
    users = UserFactory.create_batch(2)
    conversation = ConversationFactory()
    conversation.participants.set(users)

    response = get_view_for_user(
        client=client,
        viewname="direct_messages:direct-message-create",
        reverse_kwargs={"pk": conversation.pk},
        user=users[0],
        method=client.post,
        data={"message": "🙈"},
    )

    assert response.status_code == 302
    assert response.url == conversation.get_absolute_url()

    conversation.refresh_from_db()

    assert {*conversation.direct_messages.last().unread_by.all()} == {users[1]}


@pytest.mark.django_db
def test_direct_message_unread_with_mute(client):
    target, source, other = UserFactory.create_batch(3)
    conversation = ConversationFactory()
    conversation.participants.set([target, source, other])

    MuteFactory(target=target, source=source)
    MuteFactory(target=other, source=target)

    response = get_view_for_user(
        client=client,
        viewname="direct_messages:direct-message-create",
        reverse_kwargs={"pk": conversation.pk},
        user=target,
        method=client.post,
        data={"message": "🙈"},
    )

    assert response.status_code == 302
    assert response.url == conversation.get_absolute_url()

    conversation.refresh_from_db()

    assert {*conversation.direct_messages.last().unread_by.all()} == {other}


@pytest.mark.django_db
def test_mark_spam(client):
    users = UserFactory.create_batch(2)
    conversation = ConversationFactory()
    conversation.participants.set(users)
    message = DirectMessageFactory(conversation=conversation, sender=users[0])

    response = get_view_for_user(
        client=client,
        viewname="direct_messages:direct-message-report-spam",
        reverse_kwargs={"conversation_pk": conversation.pk, "pk": message.pk},
        user=users[1],
        method=client.post,
        data={"is_reported_as_spam": True},
    )

    assert response.status_code == 302
    assert response.url == conversation.get_absolute_url()

    message.refresh_from_db()

    assert message.is_reported_as_spam


@pytest.mark.django_db
def test_mute_form(client):
    users = UserFactory.create_batch(2)
    conversation = ConversationFactory()
    conversation.participants.set(users)

    response = get_view_for_user(
        client=client,
        viewname="direct_messages:mute-create",
        reverse_kwargs={"username": users[0].username},
        user=users[0],
        method=client.post,
        data={"conversation": conversation.pk},
    )
    assert response.status_code == 200
    assert response.context["form"].errors == {
        "__all__": ["You cannot mute yourself"]
    }

    response = get_view_for_user(
        client=client,
        viewname="direct_messages:mute-create",
        reverse_kwargs={"username": users[1].username},
        user=users[0],
        method=client.post,
        data={"conversation": conversation.pk},
    )
    assert response.status_code == 302
    assert response.url == conversation.get_absolute_url()

    response = get_view_for_user(
        client=client,
        viewname="direct_messages:mute-create",
        reverse_kwargs={"username": users[1].username},
        user=users[0],
        method=client.post,
        data={"conversation": conversation.pk},
    )
    assert response.status_code == 200
    assert response.context["form"].errors == {
        "__all__": ["Mute with this Target and Source already exists."]
    }


@pytest.mark.django_db
def test_mute_delete_redirect(client):
    users = UserFactory.create_batch(2)
    conversation = ConversationFactory()
    conversation.participants.set(users)

    mute = MuteFactory(source=users[0], target=users[1])

    response = get_view_for_user(
        client=client,
        viewname="direct_messages:mute-delete",
        reverse_kwargs={"username": users[1].username},
        user=users[0],
        method=client.post,
        data={"conversation": conversation.pk},
    )
    assert response.status_code == 302
    assert response.url == conversation.get_absolute_url()

    with pytest.raises(Mute.DoesNotExist):
        mute.refresh_from_db()
