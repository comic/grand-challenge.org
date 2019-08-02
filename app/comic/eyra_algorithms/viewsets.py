from django_filters import rest_framework as filters
from rest_framework.viewsets import ModelViewSet

from comic.eyra_algorithms.models import Implementation, Job, Interface, Algorithm
from comic.eyra_algorithms.serializers import ImplementationSerializer, JobSerializer, InterfaceSerializer, \
    AlgorithmSerializer
from comic.eyra_users.permissions import EyraPermissions


class ImplementationViewSet(ModelViewSet):
    # queryset = Algorithm.objects.exclude(output_type__name__exact='OutputMetrics')
    queryset = Implementation.objects.all()
    serializer_class = ImplementationSerializer
    permission_classes = (EyraPermissions,)
    filterset_fields = ['creator']

    def perform_create(self, serializer):
        # Add the logged in user as the challenge creator
        serializer.save(creator=self.request.user)


class AlgorithmFilter(filters.FilterSet):
    has_admin = filters.NumberFilter(method='has_admin_filter')

    class Meta:
        model = Algorithm
        fields = ['creator', 'has_admin']

    def has_admin_filter(self, queryset, name, value):
        return queryset.filter(admin_group__user__id__contains=value)


class AlgorithmViewSet(ModelViewSet):
    # queryset = Algorithm.objects.exclude(output_type__name__exact='OutputMetrics')
    queryset = Algorithm.objects.all()
    serializer_class = AlgorithmSerializer
    permission_classes = (EyraPermissions,)
    filterset_class = AlgorithmFilter

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
