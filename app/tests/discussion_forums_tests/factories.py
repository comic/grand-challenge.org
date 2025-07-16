import factory

from grandchallenge.discussion_forums.models import (
    Forum,
    ForumPost,
    ForumTopic,
)
from tests.factories import ChallengeFactory, UserFactory


class ForumFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Forum

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # prevent Django from creating a Forum directly
        # because forums require a parent object (i.e. a challenge)
        # and are normally created through the parent object
        challenge = ChallengeFactory(display_forum_link=True)
        return challenge.discussion_forum


class ForumTopicFactory(factory.django.DjangoModelFactory):
    creator = factory.SubFactory(UserFactory)
    forum = factory.LazyAttribute(
        lambda o: ChallengeFactory(display_forum_link=True).discussion_forum
    )

    class Meta:
        model = ForumTopic

    @factory.post_generation
    def post_count(self, create, extracted, **kwargs):
        if not create:
            return
        num_posts = int(extracted) if extracted is not None else 0
        ForumPostFactory.create_batch(num_posts, topic=self)


class ForumPostFactory(factory.django.DjangoModelFactory):
    creator = factory.SubFactory(UserFactory)
    topic = factory.SubFactory(ForumTopicFactory)

    class Meta:
        model = ForumPost
