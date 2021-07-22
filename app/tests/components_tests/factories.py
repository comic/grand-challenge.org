import factory
from factory.fuzzy import FuzzyChoice

from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)


class ComponentInterfaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ComponentInterface

    title = factory.Sequence(lambda n: f"Component Interface {n}")
    kind = FuzzyChoice(ComponentInterface.Kind.values)
    default_value = None
    relative_path = factory.Sequence(lambda n: f"interface-{n}")


class ComponentInterfaceValueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ComponentInterfaceValue

    pk = factory.Sequence(lambda n: n + 9999999)
    interface = factory.SubFactory(ComponentInterfaceFactory)
