import pytest

from grandchallenge.discussion_forums.models import Post, Topic
from tests.discussion_forums_tests.factories import PostFactory, TopicFactory


@pytest.mark.django_db
def test_delete_only_post_also_deletes_topic():
    topic = TopicFactory()
    post1, post2 = PostFactory.create_batch(2, topic=topic)

    assert not post1.is_alone
    assert not post2.is_alone

    post2.delete()
    assert post1.is_alone

    post1.delete()
    assert Topic.objects.count() == 0
    assert Post.objects.count() == 0


@pytest.mark.django_db
def test_adding_post_udates_last_post_on_topic():
    topic = TopicFactory()
    post = PostFactory(topic=topic)
    assert topic.last_post_on == post.created

    post2 = PostFactory(topic=topic)
    assert topic.last_post_on == post2.created
