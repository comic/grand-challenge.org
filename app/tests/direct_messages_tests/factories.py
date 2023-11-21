import factory

from grandchallenge.direct_messages.models import (
    Conversation,
    DirectMessage,
    Mute,
)
from tests.factories import UserFactory


class ConversationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Conversation


class DirectMessageFactory(factory.django.DjangoModelFactory):
    conversation = factory.SubFactory(ConversationFactory)
    sender = factory.SubFactory(UserFactory)

    class Meta:
        model = DirectMessage


class MuteFactory(factory.django.DjangoModelFactory):
    source = factory.SubFactory(UserFactory)
    target = factory.SubFactory(UserFactory)

    class Meta:
        model = Mute
