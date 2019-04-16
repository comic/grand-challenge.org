from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from grandchallenge.eyra_algorithms.models import Implementation
from grandchallenge.eyra_algorithms.serializers import ImplementationSerializer
from grandchallenge.eyra_benchmarks.models import Benchmark, Submission
from grandchallenge.eyra_benchmarks.serializers import BenchmarkSerializer, SubmissionSerializer
from grandchallenge.eyra_users.permissions import EyraDjangoModelPermissions, EyraDjangoModelOrObjectPermissions, \
    EyraPermissions


class BenchmarkViewSet(ModelViewSet):
    queryset = Benchmark.objects.all()
    serializer_class = BenchmarkSerializer
    permission_classes = (EyraPermissions,)

    def perform_create(self, serializer):
        # Add the logged in user as the challenge creator
        serializer.save(creator=self.request.user)


class SubmissionViewSet(ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = (EyraPermissions,)
    # filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ['benchmark']

    def perform_create(self, serializer):
        # Add the logged in user as the challenge creator
        serializer.save(creator=self.request.user)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def algorithm_submission(request):
    # fields in request.data:
    # - description (for algo)
    # - name (for algo? for submission?)
    # - container (name of container)
    # - benchmark (id of benchmark)
    benchmark_id = request.data.get('benchmark', None)
    if not benchmark_id:
        raise DRFValidationError("Benchmark UUID required")
    try:
        benchmark: Benchmark = Benchmark.objects.get(pk=benchmark_id)
    except (DjangoValidationError, Benchmark.DoesNotExist) as e:
        raise DRFValidationError(f"Invalid benchmark UUID {benchmark_id}")

    algorithm_name = request.data.get('name', None)
    if not algorithm_name:
        raise DRFValidationError("Name required")

    implementation = Implementation(
        creator=request.user,
        # creator=User.objects.first(),
        interface=benchmark.interface,
        description=request.data.get('description', ''),
        container=request.data.get('container', ''),
        name=algorithm_name,
    )
    try:
        implementation.full_clean(exclude=None)
        implementation.save()
    except IntegrityError as e:
        raise DRFValidationError("Implementation name already exists")

    submission = Submission(
        implementation=implementation,
        benchmark=benchmark,
        creator=request.user,
        # creator=User.objects.first(),
        name=f"{implementation.name} on {benchmark.name}"
    )

    submission.save()

    return Response(ImplementationSerializer(implementation).data)
