import factory

from grandchallenge.components.models import ComponentInterface


class ComponentInterfaceFactory(factory.DjangoModelFactory):
    class Meta:
        model = ComponentInterface

    title = factory.Sequence(lambda n: f"Component Interface {n}")
    relative_path = factory.Sequence(lambda n: f"interface-{n}")
