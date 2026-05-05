import factory

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmImage,
    AlgorithmInterface,
    AlgorithmModel,
    AlgorithmPermissionRequest,
    AlgorithmUserCredit,
    Endpoint,
    EndpointStatusChoices,
    Invocation,
    Job,
)
from grandchallenge.components.schemas import GPUTypeChoices
from grandchallenge.reader_studies.models import (
    ReaderStudyAlgorithm,
    ReaderStudyAlgorithmImplementation,
)
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import (
    ImageFactory,
    UserFactory,
    WorkstationFactory,
    hash_sha256,
)


class AlgorithmFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Algorithm

    title = factory.sequence(lambda n: f"Algorithm {n}")
    logo = factory.django.ImageField()
    workstation = factory.SubFactory(WorkstationFactory)


class AlgorithmImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AlgorithmImage

    algorithm = factory.SubFactory(AlgorithmFactory)
    creator = factory.SubFactory(UserFactory)
    image = factory.django.FileField()
    image_sha256 = factory.sequence(lambda n: hash_sha256(f"image{n}"))


class AlgorithmModelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AlgorithmModel

    algorithm = factory.SubFactory(AlgorithmFactory)
    creator = factory.SubFactory(UserFactory)
    model = factory.django.FileField()
    checksum = factory.sequence(lambda n: hash_sha256(f"image{n}"))


class AlgorithmJobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Job
        skip_postgeneration_save = True

    algorithm_image = factory.SubFactory(AlgorithmImageFactory)
    creator = factory.SubFactory(UserFactory)
    requires_memory_gb = 4
    requires_gpu_type = GPUTypeChoices.NO_GPU

    @factory.post_generation
    def files(self, create, extracted, **kwargs):
        # See https://factoryboy.readthedocs.io/en/latest/recipes.html#simple-many-to-many-relationship
        if not create:
            return
        if extracted:
            self.inputs.set([*extracted])
        if create and not extracted:
            self.inputs.set(
                [ComponentInterfaceValueFactory(image=ImageFactory())]
            )


class AlgorithmPermissionRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AlgorithmPermissionRequest

    algorithm = factory.SubFactory(AlgorithmFactory)
    user = factory.SubFactory(UserFactory)


class AlgorithmUserCreditFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AlgorithmUserCredit

    user = factory.SubFactory(UserFactory)
    algorithm = factory.SubFactory(AlgorithmFactory)


class AlgorithmInterfaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AlgorithmInterface

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        inputs = kwargs.pop("inputs", None)
        outputs = kwargs.pop("outputs", None)
        if not inputs:
            inputs = [ComponentInterfaceFactory()]
        if not outputs:
            outputs = [ComponentInterfaceFactory()]
        return manager.create(*args, inputs=inputs, outputs=outputs, **kwargs)


class ReaderStudyAlgorithmFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReaderStudyAlgorithm


class ReaderStudyAlgorithmImplementationFactory(
    factory.django.DjangoModelFactory
):
    class Meta:
        model = ReaderStudyAlgorithmImplementation

    algorithm = factory.SubFactory(AlgorithmFactory)
    reader_study_algorithm = factory.SubFactory(ReaderStudyAlgorithmFactory)


class EndpointFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Endpoint

    creator = factory.SubFactory(UserFactory)
    algorithm_image = factory.SubFactory(AlgorithmImageFactory)
    algorithm_model = factory.SubFactory(AlgorithmModelFactory)
    requires_gpu_type = GPUTypeChoices.NO_GPU
    requires_memory_gb = 4


class InvocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invocation

    endpoint = factory.SubFactory(
        EndpointFactory, status=EndpointStatusChoices.RUNNING
    )
    algorithm_interface = factory.SubFactory(AlgorithmInterfaceFactory)
    time_limit = 60
