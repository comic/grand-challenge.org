import pytest

from grandchallenge.discussion_forums.models import (
    ForumPost,
    ForumTopic,
    ForumTopicKindChoices,
)
from tests.discussion_forums_tests.factories import (
    ForumFactory,
    ForumPostFactory,
    ForumTopicFactory,
)
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
            "kind": ForumTopicKindChoices.DEFAULT,
            "content": "Some post content",
        },
    )
    assert response.status_code == 302

    assert ForumTopic.objects.count() == 1
    assert ForumPost.objects.count() == 1

    topic = ForumTopic.objects.first()
    assert topic.forum == forum
    assert topic.creator == user
    assert topic.kind == ForumTopicKindChoices.DEFAULT
    assert topic.subject == "First topic"

    post = ForumPost.objects.first()
    assert post.topic == topic
    assert post.creator == user
    assert post.content == "Some post content"


@pytest.mark.parametrize(
    "viewname, participant_status_code, detail",
    (
        ["discussion-forums:topic-create", 200, False],
        ["discussion-forums:topic-delete", 403, True],
    ),
)
@pytest.mark.django_db
def test_discussion_forum_topic_views_permissions(
    client, viewname, participant_status_code, detail
):
    forum = ForumFactory()
    user, participant, admin = UserFactory.create_batch(3)
    forum.linked_challenge.add_admin(admin)
    forum.linked_challenge.add_participant(participant)

    if detail:
        topic = ForumTopicFactory(forum=forum, creator=participant)
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


@pytest.mark.parametrize(
    "viewname, detail, admin_status_code, post_creator_status_code, participant_status_code",
    (
        ["discussion-forums:post-create", False, 200, 200, 200],
        ["discussion-forums:post-delete", True, 200, 200, 403],
        ["discussion-forums:post-update", True, 403, 200, 403],
    ),
)
@pytest.mark.django_db
def test_discussion_forum_post_views_permissions(
    client,
    viewname,
    detail,
    admin_status_code,
    post_creator_status_code,
    participant_status_code,
):
    forum = ForumFactory()
    participant, post_creator, admin = UserFactory.create_batch(3)
    forum.linked_challenge.add_admin(admin)
    forum.linked_challenge.add_participant(participant)
    forum.linked_challenge.add_participant(post_creator)

    topic = ForumTopicFactory(forum=forum, creator=admin)
    if detail:
        post = ForumPostFactory(topic=topic, creator=post_creator)
        extra_kwargs = {"pk": post.pk}
    else:
        extra_kwargs = {}

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=participant,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
            "slug": topic.slug,
            **extra_kwargs,
        },
    )
    assert response.status_code == participant_status_code

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=post_creator,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
            "slug": topic.slug,
            **extra_kwargs,
        },
    )
    assert response.status_code == post_creator_status_code

    response = get_view_for_user(
        viewname=viewname,
        client=client,
        user=admin,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
            "slug": topic.slug,
            **extra_kwargs,
        },
    )
    assert response.status_code == admin_status_code


@pytest.mark.django_db
def test_discussion_forum_topic_list_permission_filter(client):
    forum = ForumFactory()
    user, participant, admin = UserFactory.create_batch(3)
    forum.linked_challenge.add_admin(admin)
    forum.linked_challenge.add_participant(participant)

    ForumTopicFactory.create_batch(5, forum=forum)
    ForumTopicFactory.create_batch(5, forum=ForumFactory())

    response = get_view_for_user(
        viewname="discussion-forums:topic-list",
        client=client,
        user=user,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
        },
    )
    assert response.status_code == 403

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
            ForumTopic.objects.filter(forum=forum).all()
        )


@pytest.mark.django_db
def test_discussion_forum_topic_post_list_permission_filter(client):
    forum = ForumFactory()
    user, participant, admin = UserFactory.create_batch(3)
    forum.linked_challenge.add_admin(admin)
    forum.linked_challenge.add_participant(participant)

    topic1 = ForumTopicFactory(forum=forum, post_count=3)
    ForumTopicFactory(forum=forum, post_count=3)

    response = get_view_for_user(
        viewname="discussion-forums:topic-post-list",
        client=client,
        user=user,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
            "slug": topic1.slug,
        },
    )
    assert response.status_code == 403

    for user in [participant, admin]:
        response = get_view_for_user(
            viewname="discussion-forums:topic-post-list",
            client=client,
            user=user,
            reverse_kwargs={
                "challenge_short_name": forum.linked_challenge.short_name,
                "slug": topic1.slug,
            },
        )
        # admin and participants can access page and will see topics for this topic only
        assert response.status_code == 200
        assert response.context["object_list"].count() == 3
        assert list(response.context["object_list"]) == list(
            ForumPost.objects.filter(topic=topic1).all()
        )


@pytest.mark.django_db
def test_topic_deletion(client):
    creator, admin = UserFactory.create_batch(2)
    forum = ForumFactory()
    forum.linked_challenge.add_admin(admin)
    forum.linked_challenge.add_participant(creator)

    topic = ForumTopicFactory(forum=forum, creator=creator, post_count=3)
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
    assert ForumTopic.objects.count() == 1
    assert topic.posts.count() == ForumPost.objects.count() == 3

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
    assert ForumTopic.objects.count() == 0
    assert ForumPost.objects.count() == 0


@pytest.mark.django_db
def test_post_deletion(client):
    creator, admin = UserFactory.create_batch(2)
    forum = ForumFactory()
    forum.linked_challenge.add_admin(admin)
    forum.linked_challenge.add_participant(creator)

    topic = ForumTopicFactory(forum=forum, creator=creator, post_count=2)
    post1, post2 = topic.posts.all()

    assert topic.posts.count() == 2
    assert topic.last_post_on == post2.created

    response = get_view_for_user(
        viewname="discussion-forums:post-delete",
        client=client,
        method=client.post,
        user=admin,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
            "slug": topic.slug,
            "pk": post2.pk,
        },
    )
    assert response.status_code == 302
    # deleting the last post, updates the last_post_on time on the topic
    topic.refresh_from_db()
    assert topic.posts.count() == 1
    assert list(topic.posts.all()) == [post1]
    assert topic.last_post_on == post1.created

    response = get_view_for_user(
        viewname="discussion-forums:post-delete",
        client=client,
        method=client.post,
        user=admin,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
            "slug": topic.slug,
            "pk": post1.pk,
        },
    )
    assert response.status_code == 302
    assert ForumPost.objects.count() == 0
    # deleting the last post of a topic also deletes the topic
    assert ForumTopic.objects.count() == 0


@pytest.mark.django_db
def test_post_create(client):
    forum = ForumFactory()
    user = UserFactory()
    forum.linked_challenge.add_admin(user)
    topic = ForumTopicFactory(forum=forum, creator=user)

    assert topic.posts.count() == 1

    response = get_view_for_user(
        viewname="discussion-forums:post-create",
        client=client,
        method=client.post,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
            "slug": topic.slug,
        },
        user=user,
        data={
            "topic": topic.pk,
            "creator": user.pk,
            "content": "New post",
        },
    )
    assert response.status_code == 302
    assert topic.posts.count() == 2

    post = ForumPost.objects.last()
    assert post.topic == topic
    assert post.creator == user
    assert post.content == "New post"


@pytest.mark.django_db
def test_post_update(client):
    creator, admin = UserFactory.create_batch(2)
    forum = ForumFactory()
    forum.linked_challenge.add_admin(admin)
    forum.linked_challenge.add_participant(creator)

    topic = ForumTopicFactory(forum=forum, creator=creator, post_count=0)
    post = ForumPostFactory(topic=topic, creator=creator)

    assert topic.posts.count() == 1

    response = get_view_for_user(
        viewname="discussion-forums:post-update",
        client=client,
        method=client.post,
        user=creator,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
            "slug": topic.slug,
            "pk": post.pk,
        },
        data={
            "topic": topic.pk,
            "creator": creator.pk,
            "content": "Updated content",
        },
    )
    assert response.status_code == 302
    post.refresh_from_db()
    assert post.content == "Updated content"
