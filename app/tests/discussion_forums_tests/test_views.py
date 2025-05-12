import pytest

from grandchallenge.discussion_forums.models import (
    Post,
    Topic,
    TopicTypeChoices,
)
from tests.discussion_forums_tests.factories import TopicFactory
from tests.factories import ChallengeFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_topic_create(client):
    challenge = ChallengeFactory(display_forum_link=True)
    user = UserFactory()
    challenge.add_admin(user)

    response = get_view_for_user(
        viewname="discussion-forums:topic-create",
        client=client,
        method=client.post,
        reverse_kwargs={"challenge_short_name": challenge.short_name},
        user=user,
        data={
            "forum": challenge.discussion_forum.pk,
            "creator": user.pk,
            "subject": "First topic",
            "type": TopicTypeChoices.DEFAULT,
            "content": "Some post content",
        },
    )
    assert response.status_code == 302

    assert Topic.objects.count() == 1
    assert Post.objects.count() == 1

    topic = Topic.objects.first()
    assert topic.forum == challenge.discussion_forum
    assert topic.creator == user
    assert topic.type == TopicTypeChoices.DEFAULT
    assert topic.subject == "First topic"

    post = Post.objects.first()
    assert post.topic == topic
    assert post.creator == user
    assert post.subject == "First topic"
    assert post.content == "Some post content"


@pytest.mark.parametrize(
    "viewname, detail",
    (
        ["discussion-forums:topic-create", False],
        ["discussion-forums:topic-delete", True],
        ["discussion-forums:topic-detail", True],
    ),
)
@pytest.mark.django_db
def test_discussion_forum_views_permissions(client, viewname, detail):
    challenge = ChallengeFactory(display_forum_link=True)
    user, participant, admin = UserFactory.create_batch(3)
    challenge.add_admin(admin)
    challenge.add_participant(participant)

    if detail:
        topic = TopicFactory(
            forum=challenge.discussion_forum, creator=participant
        )
        extra_kwargs = {"pk": topic.pk}
    else:
        extra_kwargs = {}

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=user,
        reverse_kwargs={
            "challenge_short_name": challenge.short_name,
            **extra_kwargs,
        },
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=participant,
        reverse_kwargs={
            "challenge_short_name": challenge.short_name,
            **extra_kwargs,
        },
    )
    assert response.status_code == 200

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=admin,
        reverse_kwargs={
            "challenge_short_name": challenge.short_name,
            **extra_kwargs,
        },
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_discussion_forum_topic_list_permission_filter(client):
    challenge = ChallengeFactory(display_forum_link=True)
    user, participant, admin = UserFactory.create_batch(3)
    challenge.add_admin(admin)
    challenge.add_participant(participant)

    challenge2 = ChallengeFactory(display_forum_link=True)

    TopicFactory.create_batch(5, forum=challenge.discussion_forum)
    TopicFactory.create_batch(5, forum=challenge2.discussion_forum)

    response = get_view_for_user(
        viewname="discussion-forums:topic-list",
        client=client,
        user=user,
        reverse_kwargs={
            "challenge_short_name": challenge.short_name,
        },
    )
    assert response.status_code == 200
    assert response.context["object_list"].count() == 0

    for user in [participant, admin]:
        response = get_view_for_user(
            viewname="discussion-forums:topic-list",
            client=client,
            user=user,
            reverse_kwargs={
                "challenge_short_name": challenge.short_name,
            },
        )
        # admin and participants can access page and will see topics for this forum only
        assert response.status_code == 200
        assert response.context["object_list"].count() == 5
        assert list(response.context["object_list"]) == list(
            Topic.objects.filter(forum=challenge.discussion_forum).all()
        )
