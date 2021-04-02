import factory
from django.utils.text import slugify
from factory import fuzzy
from factory.fuzzy import FuzzyChoice
from faker import Faker
from machina.apps.forum_conversation.models import Post
from machina.core.db.models import get_model

from tests.factories import UserFactory

faker = Faker()

Topic = get_model("forum_conversation", "Topic")
Forum = get_model("forum", "Forum")

NAMES = [faker.name() for i in range(10)]


class ForumFactory(factory.django.DjangoModelFactory):
    name = factory.LazyAttribute(lambda obj: FuzzyChoice(NAMES).fuzz())
    slug = factory.LazyAttribute(lambda t: slugify(t.name))

    # Link forum specific
    link = faker.uri()

    class Meta:
        model = Forum


class TopicFactory(factory.django.DjangoModelFactory):
    forum = factory.SubFactory(ForumFactory)
    poster = factory.SubFactory(UserFactory)
    status = Topic.TOPIC_UNLOCKED
    subject = factory.LazyAttribute(lambda t: faker.text(max_nb_chars=200))
    slug = factory.LazyAttribute(lambda t: slugify(t.subject))

    class Meta:
        model = Topic


class PostFactory(factory.django.DjangoModelFactory):
    topic = factory.SubFactory(TopicFactory)
    poster = factory.SubFactory(UserFactory)
    subject = factory.LazyAttribute(lambda t: faker.text(max_nb_chars=200))
    content = fuzzy.FuzzyText(length=255)

    class Meta:
        model = Post
