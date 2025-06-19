import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from guardian.utils import get_anonymous_user

from grandchallenge.discussion_forums.models import (
    ForumPost,
    ForumTopic,
    ForumTopicKindChoices,
    TopicReadRecord,
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
        ["discussion-forums:topic-lock-update", 403, True],
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
            follow=True,
        )
        # admin and participants can access page and will see topics for this topic only
        assert response.status_code == 200
        assert response.context["object_list"].count() == 3
        assert list(response.context["object_list"]) == list(
            ForumPost.objects.filter(topic=topic1).all()
        )


@pytest.mark.django_db
def test_redirect_when_unread_posts(client):
    forum = ForumFactory()
    user = UserFactory()
    forum.linked_challenge.add_participant(user)
    topic = ForumTopicFactory(forum=forum, post_count=3)

    link_to_unread_post = (
        topic.get_unread_topic_posts_for_user(user=user)
        .first()
        .get_absolute_url()
    )

    response = get_view_for_user(
        viewname="discussion-forums:topic-post-list",
        client=client,
        user=user,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
            "slug": topic.slug,
        },
    )
    assert (
        response.status_code == 302
    )  # redirect because there are unread posts
    assert response.url == link_to_unread_post
    # all posts are now marked as read
    assert not topic.get_unread_topic_posts_for_user(user=user).exists()

    response = get_view_for_user(
        viewname="discussion-forums:topic-post-list",
        client=client,
        user=user,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
            "slug": topic.slug,
        },
    )
    assert response.status_code == 200  # no redirect when no unread posts


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
    assert topic.last_post == post2
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
    assert topic.last_post == post1
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
    topic = ForumTopicFactory(forum=forum, creator=user, post_count=1)

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


@pytest.mark.django_db
def test_topic_lock_update(client):
    topic = ForumTopicFactory()
    admin = UserFactory()
    topic.forum.linked_challenge.add_admin(admin)

    assert not topic.is_locked

    response = get_view_for_user(
        viewname="discussion-forums:topic-lock-update",
        client=client,
        method=client.post,
        user=admin,
        reverse_kwargs={
            "challenge_short_name": topic.forum.linked_challenge.short_name,
            "slug": topic.slug,
        },
        data={"is_locked": True},
    )
    assert response.status_code == 302
    topic.refresh_from_db()
    assert topic.is_locked

    response = get_view_for_user(
        viewname="discussion-forums:topic-lock-update",
        client=client,
        method=client.post,
        user=admin,
        reverse_kwargs={
            "challenge_short_name": topic.forum.linked_challenge.short_name,
            "slug": topic.slug,
        },
        data={"is_locked": False},
    )

    assert response.status_code == 302
    topic.refresh_from_db()
    assert not topic.is_locked


@pytest.mark.django_db
def test_my_posts_listview_filter(client):
    forum = ForumFactory()
    participant, admin = UserFactory.create_batch(2)
    forum.linked_challenge.add_participant(participant)
    forum.linked_challenge.add_admin(admin)

    # 3 posts from participant in this forum
    p1, p2, p3 = ForumPostFactory.create_batch(
        3, topic__forum=forum, creator=participant
    )
    # 1 post from this user in a different forum
    forum2 = ForumFactory()
    forum2.linked_challenge.add_participant(participant)
    p_diff_forum = ForumPostFactory(creator=participant, topic__forum=forum2)
    # 1 post from another user in this forum
    p_diff_user = ForumPostFactory(topic__forum=forum)
    # 1 post from admin in this forum
    p_admin = ForumPostFactory(creator=admin, topic__forum=forum)

    participant_response = get_view_for_user(
        viewname="discussion-forums:my-posts",
        client=client,
        user=participant,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
        },
    )
    assert participant_response.status_code == 200
    # all posts from this user, not just in the current forum, should be listed
    assert participant_response.context["object_list"].count() == 4
    assert p_diff_user not in participant_response.context["object_list"]
    assert {p1, p2, p3, p_diff_forum} == set(
        participant_response.context["object_list"].all()
    )

    admin_response = get_view_for_user(
        viewname="discussion-forums:my-posts",
        client=client,
        user=admin,
        reverse_kwargs={
            "challenge_short_name": forum.linked_challenge.short_name,
        },
    )
    assert admin_response.status_code == 200
    # admin should only see their own posts, not those of participants
    assert admin_response.context["object_list"].count() == 1
    assert p_admin in admin_response.context["object_list"]


@pytest.mark.django_db
def test_users_cannot_post_to_locked_topic(client):
    topic = ForumTopicFactory(post_count=1)
    user, admin = UserFactory.create_batch(2)
    topic.forum.linked_challenge.add_participant(user)
    topic.forum.linked_challenge.add_admin(admin)

    post_count = topic.posts.count()

    for u in [user, admin]:
        response = get_view_for_user(
            viewname="discussion-forums:post-create",
            client=client,
            method=client.post,
            user=u,
            reverse_kwargs={
                "challenge_short_name": topic.forum.linked_challenge.short_name,
                "slug": topic.slug,
            },
            data={
                "topic": topic.pk,
                "creator": u.pk,
                "content": "New post",
            },
        )
        post_count += 1
        assert response.status_code == 302
        assert topic.posts.count() == post_count

    # locking revokes the permission to create posts
    topic.is_locked = True
    topic.save()

    for u in [user, admin]:
        response = get_view_for_user(
            viewname="discussion-forums:post-create",
            client=client,
            method=client.post,
            user=u,
            reverse_kwargs={
                "challenge_short_name": topic.forum.linked_challenge.short_name,
                "slug": topic.slug,
            },
            data={
                "topic": topic.pk,
                "creator": u.pk,
                "content": "New post",
            },
        )
        assert response.status_code == 403
        assert topic.posts.count() == post_count


@pytest.mark.django_db
def test_topic_marked_as_read(client):
    topic = ForumTopicFactory(post_count=3)
    user = UserFactory()
    topic.forum.linked_challenge.add_participant(user)

    assert not TopicReadRecord.objects.filter(user=user, topic=topic).exists()

    # accessing the topic detail view, will mark the topic as read by this user
    response = get_view_for_user(
        viewname="discussion-forums:topic-post-list",
        client=client,
        user=user,
        reverse_kwargs={
            "slug": topic.slug,
            "challenge_short_name": topic.forum.linked_challenge.short_name,
        },
        follow=True,
    )
    assert response.status_code == 200
    assert TopicReadRecord.objects.filter(user=user, topic=topic).exists()

    old_modified_time = TopicReadRecord.objects.get(
        user=user, topic=topic
    ).modified

    # accessing the topic detail view again, will update the modified time
    response = get_view_for_user(
        viewname="discussion-forums:topic-post-list",
        client=client,
        user=user,
        reverse_kwargs={
            "slug": topic.slug,
            "challenge_short_name": topic.forum.linked_challenge.short_name,
        },
    )
    assert response.status_code == 200
    assert (
        TopicReadRecord.objects.get(user=user, topic=topic).modified
        > old_modified_time
    )


@pytest.mark.django_db
def test_topic_read_status_not_tracked_for_anonymous_user(client):
    topic = ForumTopicFactory(post_count=3)
    user = UserFactory()
    topic.forum.linked_challenge.add_participant(user)

    TopicReadRecord.objects.filter(topic=topic).all().delete()

    # accessing the topic detail view as anonymous user will fail with permission error and will not create a record
    response = get_view_for_user(
        viewname="discussion-forums:topic-post-list",
        client=client,
        reverse_kwargs={
            "slug": topic.slug,
            "challenge_short_name": topic.forum.linked_challenge.short_name,
        },
        follow=True,
    )
    assert response.status_code == 403
    assert not TopicReadRecord.objects.filter(topic=topic).exists()

    # our custom method ignores anonymous users as well
    topic.mark_as_read(user=get_anonymous_user())
    assert not TopicReadRecord.objects.filter(topic=topic).exists()

    # directly creating a record for the anonymous user also does not work
    with pytest.raises(ValidationError):
        TopicReadRecord.objects.create(user=get_anonymous_user(), topic=topic)


@pytest.mark.django_db
def test_queries_on_topic_list_view(client, django_assert_num_queries):
    forum = ForumFactory()
    user = UserFactory()
    forum.linked_challenge.add_admin(user)

    ForumTopicFactory.create_batch(5, forum=forum, post_count=0)

    with CaptureQueriesContext(connection) as context:
        response = get_view_for_user(
            viewname="discussion-forums:topic-list",
            client=client,
            user=user,
            reverse_kwargs={
                "challenge_short_name": forum.linked_challenge.short_name,
            },
        )
    assert response.status_code == 200

    initial_query_count = len(context)

    # adding 5 more does not result in more queries
    ForumTopicFactory.create_batch(5, forum=forum)
    with django_assert_num_queries(initial_query_count):
        get_view_for_user(
            viewname="discussion-forums:topic-list",
            client=client,
            user=user,
            reverse_kwargs={
                "challenge_short_name": forum.linked_challenge.short_name,
            },
        )
