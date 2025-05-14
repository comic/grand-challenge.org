import pytest

from grandchallenge.discussion_forums.models import (
    Post,
    Topic,
    TopicKindChoices,
)
from tests.discussion_forums_tests.factories import ForumFactory, TopicFactory
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_topic_create(client):
    forum = ForumFactory()
    user = UserFactory()
    forum.linked_challenge.add_admin(user)

    response = get_view_for_user(
        viewname="discussion-forums:topic-create",
        client=client,
        method=client.post,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name
        },
        user=user,
        data={
            "forum": forum.pk,
            "creator": user.pk,
            "subject": "First topic",
            "type": TopicKindChoices.DEFAULT,
            "content": "Some post content",
        },
    )
    assert response.status_code == 302

    assert Topic.objects.count() == 1
    assert Post.objects.count() == 1

    topic = Topic.objects.first()
    assert topic.forum == forum
    assert topic.creator == user
    assert topic.type == TopicKindChoices.DEFAULT
    assert topic.subject == "First topic"

    post = Post.objects.first()
    assert post.topic == topic
    assert post.creator == user
    assert post.subject == "First topic"
    assert post.content == "Some post content"


@pytest.mark.parametrize(
    "viewname, participant_status_code, detail",
    (
        ["discussion-forums:topic-create", 200, False],
        ["discussion-forums:topic-delete", 403, True],
        ["discussion-forums:topic-detail", 200, True],
    ),
)
@pytest.mark.django_db
def test_discussion_forum_views_permissions(
    client, viewname, participant_status_code, detail
):
    forum = ForumFactory()
    user, participant, admin = UserFactory.create_batch(3)
    forum.linked_challenge.add_admin(admin)
    forum.linked_challenge.add_participant(participant)

    if detail:
        topic = TopicFactory(forum=forum, creator=participant)
        extra_kwargs = {"slug": topic.slug}
    else:
        extra_kwargs = {}

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=user,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
            **extra_kwargs,
        },
    )
    assert response.status_code == 403

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=participant,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
            **extra_kwargs,
        },
    )
    assert response.status_code == participant_status_code

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=admin,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
            **extra_kwargs,
        },
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_discussion_forum_topic_list_permission_filter(client):
    forum = ForumFactory()
    user, participant, admin = UserFactory.create_batch(3)
    forum.linked_challenge.add_admin(admin)
    forum.linked_challenge.add_participant(participant)

    TopicFactory.create_batch(5, forum=forum)
    TopicFactory.create_batch(5, forum=ForumFactory())

    response = get_view_for_user(
        viewname="discussion-forums:topic-list",
        client=client,
        user=user,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
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
                "challenge_short_name": forum.linked_challenge.short_name,
            },
        )
        # admin and participants can access page and will see topics for this forum only
        assert response.status_code == 200
        assert response.context["object_list"].count() == 5
        assert list(response.context["object_list"]) == list(
            Topic.objects.filter(forum=forum).all()
        )


@pytest.mark.django_db
def test_topic_deletion(client):
    creator, admin = UserFactory.create_batch(2)
    forum = ForumFactory()
    forum.linked_challenge.add_admin(admin)
    forum.linked_challenge.add_participant(creator)

    topic = TopicFactory(forum=forum, creator=creator, post_count=3)
    assert topic.posts.count() == 3

    response = get_view_for_user(
        viewname="discussion-forums:topic-delete",
        client=client,
        method=client.post,
        user=creator,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
            "slug": topic.slug,
        },
    )
    # topic creator cannot delete
    assert response.status_code == 403
    assert Topic.objects.count() == 1
    assert topic.posts.count() == Post.objects.count() == 3

    response = get_view_for_user(
        viewname="discussion-forums:topic-delete",
        client=client,
        method=client.post,
        user=admin,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
            "slug": topic.slug,
        },
    )
    # admin can delete and deleting topic also deletes associated posts
    assert response.status_code == 302
    assert Topic.objects.count() == 0
    assert Post.objects.count() == 0
