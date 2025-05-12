import pytest

from grandchallenge.discussion_forums.forms import TopicForm
from grandchallenge.discussion_forums.models import TopicTypeChoices
from tests.factories import ChallengeFactory, UserFactory


@pytest.mark.django_db
def test_topic_form_presets():
    challenge = ChallengeFactory(display_forum_link=True)
    participant, admin = UserFactory.create_batch(2)
    challenge.add_admin(admin)
    challenge.add_participant(participant)

    participant_form = TopicForm(
        forum=challenge.discussion_forum,
        user=participant,
    )

    assert participant_form.fields["creator"].initial == participant
    assert (
        participant_form.fields["forum"].initial == challenge.discussion_forum
    )

    assert participant_form.fields["type"].choices == [
        (TopicTypeChoices.DEFAULT.name, TopicTypeChoices.DEFAULT.label)
    ]

    admin_form = TopicForm(
        forum=challenge.discussion_forum,
        user=admin,
    )

    assert admin_form.fields["creator"].initial == admin
    assert admin_form.fields["forum"].initial == challenge.discussion_forum

    assert admin_form.fields["type"].choices == [
        (TopicTypeChoices.DEFAULT.name, TopicTypeChoices.DEFAULT.label),
        (TopicTypeChoices.STICKY.name, TopicTypeChoices.STICKY.label),
        (TopicTypeChoices.ANNOUNCE.name, TopicTypeChoices.ANNOUNCE.label),
    ]
