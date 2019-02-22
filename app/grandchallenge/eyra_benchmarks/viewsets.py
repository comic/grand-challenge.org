from rest_framework.permissions import BasePermission, AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet

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

    def perform_create(self, serializer):
        # Add the logged in user as the challenge creator
        serializer.save(creator=self.request.user)
