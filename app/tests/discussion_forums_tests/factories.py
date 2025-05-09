import factory

from grandchallenge.discussion_forums.models import Forum, Post, Topic
from tests.factories import UserFactory


class ForumFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Forum


class TopicFactory(factory.django.DjangoModelFactory):
    creator = factory.SubFactory(UserFactory)
    forum = factory.SubFactory(ForumFactory)

    class Meta:
        model = Topic


class PostFactory(factory.django.DjangoModelFactory):
    creator = factory.SubFactory(UserFactory)
    topic = factory.SubFactory(TopicFactory)

    class Meta:
        model = Post
