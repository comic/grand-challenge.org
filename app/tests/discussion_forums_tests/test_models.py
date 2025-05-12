import pytest

from grandchallenge.discussion_forums.models import Post, Topic
from tests.discussion_forums_tests.factories import PostFactory, TopicFactory


@pytest.mark.django_db
def test_delete_only_post_also_deletes_topic():
    topic = TopicFactory(post_count=2)

    assert topic.posts.count() == 2
    post1 = topic.posts.first()
    post2 = topic.posts.last()

    assert not post1.is_alone
    assert not post2.is_alone

    post2.delete()
    assert post1.is_alone

    post1.delete()
    assert Topic.objects.count() == 0
    assert Post.objects.count() == 0


@pytest.mark.django_db
def test_adding_post_updates_last_post_on_topic():
    topic = TopicFactory()
    assert topic.posts.count() == 1
    post = topic.posts.first()
    assert topic.last_post_on == post.created

    post2 = PostFactory(topic=topic)
    assert topic.last_post_on == post2.created
