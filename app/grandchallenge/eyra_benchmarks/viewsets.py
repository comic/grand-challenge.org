from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.models import User
from django.db import IntegrityError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import BasePermission, AllowAny, IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework import generics

from grandchallenge.eyra_algorithms.models import Algorithm
from grandchallenge.eyra_algorithms.serializers import AlgorithmSerializer
from grandchallenge.eyra_benchmarks.models import Benchmark, Submission
from grandchallenge.eyra_benchmarks.serializers import BenchmarkSerializer, SubmissionSerializer


class BenchmarkAccessPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method == "GET":
            # List
            return True
        elif request.method == "POST":
            # Create: only authenticated users
            return request.user and request.user.is_authenticated
        elif request.method == "PUT":
            # Update: only authenticated users (object permission is checked next)
            return request.user and request.user.is_authenticated
        return False

    def has_object_permission(self, request, view, obj):
        if request.method == "PUT":
            # Update: only challenge admins
            return obj.is_admin(request.user)
        return True


class BenchmarkViewSet(ModelViewSet):
    queryset = Benchmark.objects.all()
    serializer_class = BenchmarkSerializer
    permission_classes = (BenchmarkAccessPermission,)

    def perform_create(self, serializer):
        # Add the logged in user as the challenge creator
        serializer.save(creator=self.request.user)


class SubmissionViewSet(ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    # filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ['benchmark']

    def perform_create(self, serializer):
        # Add the logged in user as the challenge creator
        serializer.save(creator=self.request.user)


@api_view(['POST'])
# @permission_classes((IsAuthenticated,))
@permission_classes((AllowAny,))
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

    algorithm = Algorithm(
        creator=request.user,
        # creator=User.objects.first(),
        interface=benchmark.interface,
        description=request.data.get('description', ''),
        container=request.data.get('container', ''),
        name=algorithm_name,
    )
    try:
        algorithm.full_clean(exclude=None)
        algorithm.save()
    except IntegrityError as e:
        raise DRFValidationError("Algorithm name already exists")

    submission = Submission(
        algorithm=algorithm,
        benchmark=benchmark,
        creator=request.user,
        # creator=User.objects.first(),
        name=f"{algorithm.name} on {benchmark.name}"
    )

    submission.save()

    return Response(AlgorithmSerializer(algorithm).data)
