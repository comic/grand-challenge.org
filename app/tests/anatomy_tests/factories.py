import factory

from grandchallenge.anatomy.models import BodyRegion, BodyStructure


class BodyRegionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BodyRegion


class BodyStructureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BodyStructure

    region = factory.SubFactory(BodyRegionFactory)
