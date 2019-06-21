from django_filters import rest_framework as filters
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, DjangoObjectPermissions, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from comic.eyra_algorithms.models import Implementation, Algorithm
from comic.eyra_algorithms.serializers import ImplementationSerializer
from comic.eyra_benchmarks.models import Benchmark, Submission
from comic.eyra_benchmarks.serializers import BenchmarkSerializer, SubmissionSerializer
from comic.eyra_users.permissions import EyraDjangoModelPermissions, EyraDjangoModelOrObjectPermissions, \
    EyraPermissions


class BenchmarkFilter(filters.FilterSet):
    has_admin = filters.NumberFilter(method='has_admin_filter')

    class Meta:
        model = Benchmark
        fields = ['creator', 'has_admin']

    def has_admin_filter(self, queryset, name, value):
        return queryset.filter(admin_group__user__id__contains=value)


class BenchmarkViewSet(ModelViewSet):
    queryset = Benchmark.objects.all()
    serializer_class = BenchmarkSerializer
    permission_classes = (EyraPermissions,)
    filterset_class = BenchmarkFilter

    def perform_create(self, serializer):
        # Add the logged in user as the challenge creator
        serializer.save(creator=self.request.user)


class SubmissionViewSet(ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = (EyraPermissions,)
    # filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ['benchmark', 'creator', 'is_private']

    def perform_create(self, serializer):
        # Add the logged in user as the challenge creator
        serializer.save(creator=self.request.user)


@api_view(['POST'])
@permission_classes((IsAuthenticated,))
def algorithm_submission(request):

    benchmark_id = request.data.get('benchmark', None)
    if not benchmark_id:
        raise DRFValidationError("Benchmark UUID required")
    try:
        benchmark: Benchmark = Benchmark.objects.get(pk=benchmark_id)
    except (DjangoValidationError, Benchmark.DoesNotExist) as e:
        raise DRFValidationError(f"Invalid benchmark UUID {benchmark_id}")

    algorithm_name = request.data.get('algorithm_name', None)
    if not algorithm_name:
        raise DRFValidationError("algorithm_name required")
    implementation_name = request.data.get('implementation_name', None)
    if not implementation_name:
        raise DRFValidationError("implementation_name required")
    container_name = request.data.get('container_name', None)
    if not container_name:
        raise DRFValidationError("container_name required")
    
    try:
        algorithm = Algorithm.objects.get(name=algorithm_name)
    except Algorithm.DoesNotExist:
        algorithm = Algorithm(
            name=algorithm_name,
            description=algorithm_name,
            creator=request.user,
            interface=benchmark.interface,
        )
        algorithm.save()

    implementation = Implementation(
        creator=request.user,
        # creator=User.objects.first(),
        algorithm=algorithm,
        description=request.data.get('implementation_name'),
        image=request.data.get('container_name'),
        name=request.data.get('implementation_name'),
        version=request.data.get('version'),

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
