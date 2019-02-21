from rest_framework.permissions import BasePermission
from rest_framework.viewsets import ModelViewSet

from grandchallenge.eyra_benchmarks.models import Benchmark
from grandchallenge.eyra_benchmarks.serializers import BenchmarkSerializer


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

    def has_object_permission(self, request, view, challenge):
        if request.method == "PUT":
            # Update: only challenge admins
            return challenge.is_admin(request.user)
        return True


class EyraBenchmarkViewSet(ModelViewSet):
    queryset = Benchmark.objects.all()
    serializer_class = BenchmarkSerializer
    permission_classes = (BenchmarkAccessPermission,)

    def perform_create(self, serializer):
        # Add the logged in user as the challenge creator
        serializer.save(creator=self.request.user)
