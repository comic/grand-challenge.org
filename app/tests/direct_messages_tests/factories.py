import factory

from grandchallenge.direct_messages.models import Conversation


class ConversationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Conversation
