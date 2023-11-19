import pytest
from guardian.utils import get_anonymous_user

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
