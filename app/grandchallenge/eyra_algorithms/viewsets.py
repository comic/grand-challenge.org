from rest_framework.viewsets import ModelViewSet

from grandchallenge.eyra_algorithms.models import Implementation, Job, Interface, Algorithm
from grandchallenge.eyra_algorithms.serializers import ImplementationSerializer, JobSerializer, InterfaceSerializer, \
    AlgorithmSerializer
from grandchallenge.eyra_users.permissions import EyraPermissions


class ImplementationViewSet(ModelViewSet):
    # queryset = Algorithm.objects.exclude(output_type__name__exact='OutputMetrics')
    queryset = Implementation.objects.all()
    serializer_class = ImplementationSerializer
    permission_classes = (EyraPermissions,)

    def perform_create(self, serializer):
        # Add the logged in user as the challenge creator
        serializer.save(creator=self.request.user)


class AlgorithmViewSet(ModelViewSet):
    # queryset = Algorithm.objects.exclude(output_type__name__exact='OutputMetrics')
    queryset = Algorithm.objects.all()
    serializer_class = AlgorithmSerializer
    permission_classes = (EyraPermissions,)

    def perform_create(self, serializer):
        # Add the logged in user as the challenge creator
        serializer.save(creator=self.request.user)


class JobViewSet(ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = (EyraPermissions,)


class InterfaceViewSet(ModelViewSet):
    queryset = Interface.objects.all()
    serializer_class = InterfaceSerializer
    permission_classes = (EyraPermissions,)
