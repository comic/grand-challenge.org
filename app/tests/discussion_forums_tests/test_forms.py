import pytest

from grandchallenge.discussion_forums.forms import ForumTopicForm
from grandchallenge.discussion_forums.models import ForumTopicKindChoices
from tests.factories import ChallengeFactory, UserFactory


@pytest.mark.django_db
def test_topic_form_presets():
    challenge = ChallengeFactory(display_forum_link=True)
    participant, admin = UserFactory.create_batch(2)
    challenge.add_admin(admin)
    challenge.add_participant(participant)

    participant_form = ForumTopicForm(
        forum=challenge.discussion_forum,
        user=participant,
    )

    assert participant_form.fields["creator"].initial == participant
    assert (
        participant_form.fields["forum"].initial == challenge.discussion_forum
    )

    assert participant_form.fields["kind"].choices == [
        (
            ForumTopicKindChoices.DEFAULT.name,
            ForumTopicKindChoices.DEFAULT.label,
        )
    ]

    admin_form = ForumTopicForm(
        forum=challenge.discussion_forum,
        user=admin,
    )

    assert admin_form.fields["creator"].initial == admin
    assert admin_form.fields["forum"].initial == challenge.discussion_forum

    assert admin_form.fields["kind"].choices == [
        (
            ForumTopicKindChoices.DEFAULT.name,
            ForumTopicKindChoices.DEFAULT.label,
        ),
        (
            ForumTopicKindChoices.STICKY.name,
            ForumTopicKindChoices.STICKY.label,
        ),
        (
            ForumTopicKindChoices.ANNOUNCE.name,
            ForumTopicKindChoices.ANNOUNCE.label,
        ),
    ]
