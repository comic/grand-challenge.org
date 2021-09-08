import factory
from django.utils.text import slugify
from factory import fuzzy
from factory.fuzzy import FuzzyChoice
from faker import Faker
from machina.core.db.models import get_model

from grandchallenge.notifications.models import Notification
from tests.factories import UserFactory

faker = Faker()

Topic = get_model("forum_conversation", "Topic")
Forum = get_model("forum", "Forum")
Post = get_model("forum_conversation", "Post")

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

    # make sure that topic creation also results in post creation
    @factory.post_generation
    def create_first_topic_post(self, create, extracted, **kwargs):
        if create:
            _ = PostFactory(topic=self, poster=self.poster)
            return self


class PostFactory(factory.django.DjangoModelFactory):
    topic = factory.SubFactory(TopicFactory)
    poster = factory.SubFactory(UserFactory)
    subject = factory.LazyAttribute(lambda t: faker.text(max_nb_chars=200))
    content = fuzzy.FuzzyText(length=255)

    class Meta:
        model = Post


class NotificationFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    type = FuzzyChoice(Notification.Type.values)

    class Meta:
        model = Notification
