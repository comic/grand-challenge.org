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

    @factory.post_generation
    def posts(self, create, extracted, **kwargs):
        if create:
            PostFactory(topic=self)


class PostFactory(factory.django.DjangoModelFactory):
    creator = factory.SubFactory(UserFactory)
    topic = factory.SubFactory(TopicFactory)

    class Meta:
        model = Post
