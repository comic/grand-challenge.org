import pytest

from grandchallenge.discussion_forums.models import (
    ForumPost,
    ForumTopic,
    TopicReadRecord,
)
from tests.discussion_forums_tests.factories import (
    ForumPostFactory,
    ForumTopicFactory,
)
from tests.factories import UserFactory


@pytest.mark.django_db
def test_delete_only_post_also_deletes_topic():
    topic = ForumTopicFactory(post_count=2)

    assert topic.posts.count() == 2
    post1 = topic.posts.first()
    post2 = topic.posts.last()

    assert not post1.is_alone
    assert not post2.is_alone

    post2.delete()
    assert post1.is_alone

    post1.delete()
    assert ForumTopic.objects.count() == 0
    assert ForumPost.objects.count() == 0


@pytest.mark.django_db
def test_adding_post_updates_last_post_on_topic():
    topic = ForumTopicFactory(post_count=1)
    assert topic.posts.count() == 1
    post = topic.posts.first()
    assert topic.last_post == post
    assert topic.last_post_on == post.created

    post2 = ForumPostFactory(topic=topic)
    assert topic.last_post == post2
    assert topic.last_post_on == post2.created


@pytest.mark.django_db
def test_get_unread_topic_posts_for_user():
    topic = ForumTopicFactory(post_count=5)
    user = UserFactory()

    assert topic.get_unread_topic_posts_for_user(user=user).count() == 5

    TopicReadRecord.objects.create(user=user, topic=topic)

    assert topic.get_unread_topic_posts_for_user(user=user).count() == 0

    new_post = ForumPostFactory(topic=topic)

    assert topic.get_unread_topic_posts_for_user(user=user).count() == 1
    assert [new_post] == list(
        topic.get_unread_topic_posts_for_user(user=user).all()
    )
