from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.evaluation.models import AlgorithmEvaluation
from grandchallenge.evaluation.serializers import AlgorithmEvaluationSerializer


class AlgorithmEvaluationViewSet(ReadOnlyModelViewSet):
    queryset = AlgorithmEvaluation.objects.all()
    serializer_class = AlgorithmEvaluationSerializer
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = (
        DjangoFilterBackend,
        ObjectPermissionsFilter,
    )
    filterset_fields = ["submission"]
