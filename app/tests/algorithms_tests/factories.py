import factory
from grandchallenge.algorithms.models import AlgorithmImage, Job, Result
from tests.factories import ImageFactory


class AlgorithmImageFactory(factory.DjangoModelFactory):
    class Meta:
        model = AlgorithmImage

    title = factory.sequence(lambda n: f"Algorithm {n}")
    logo = factory.django.ImageField()


class JobFactory(factory.DjangoModelFactory):
    class Meta:
        model = Job

    algorithm_image = factory.SubFactory(AlgorithmImageFactory)
    image = factory.SubFactory(ImageFactory)


class ResultFactory(factory.DjangoModelFactory):
    class Meta:
        model = Result

    job = factory.SubFactory(JobFactory)
