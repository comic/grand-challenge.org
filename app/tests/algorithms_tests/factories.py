import factory
from grandchallenge.algorithms.models import Algorithm, Job, Result
from tests.factories import ImageFactory


class AlgorithmFactory(factory.DjangoModelFactory):
    class Meta:
        model = Algorithm

    title = factory.sequence(lambda n: f"Algorithm {n}")
    logo = factory.django.ImageField()


class JobFactory(factory.DjangoModelFactory):
    class Meta:
        model = Job

    algorithm = factory.SubFactory(AlgorithmFactory)
    image = factory.SubFactory(ImageFactory)


class ResultFactory(factory.DjangoModelFactory):
    class Meta:
        model = Result

    job = factory.SubFactory(JobFactory)