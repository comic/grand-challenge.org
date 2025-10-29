from django.conf import settings
from django.db.transaction import on_commit
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.filters import BaseFilterBackend
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.viewsets import ReadOnlyModelViewSet

from grandchallenge.core.guardian import (
    ViewObjectPermissionsFilter,
    filter_by_permission,
)
from grandchallenge.core.renderers import PaginatedCSVRenderer
from grandchallenge.evaluation.models import Evaluation
from grandchallenge.evaluation.serializers import (
    EvaluationSerializer,
    ExternalEvaluationSerializer,
    ExternalEvaluationUpdateSerializer,
)
from grandchallenge.evaluation.tasks import (
    cancel_external_evaluations_past_timeout,
)


class CanClaimEvaluation(permissions.BasePermission):
    """Object-level permission to only a user with 'claim_evaluation' permission"""

    def has_object_permission(self, request, view, obj):
        return request.user.has_perm("evaluation.claim_evaluation", obj)


class CanClaimEvaluationFilter(BaseFilterBackend):
    """Returns only evaluations for which the user has 'claim_evaluation' permission and which are in pending state"""

    def filter_queryset(self, request, queryset, view):
        return filter_by_permission(
            queryset=queryset.filter(status=Evaluation.PENDING),
            user=request.user,
            codename="claim_evaluation",
        )


class EvaluationViewSet(ReadOnlyModelViewSet):
    queryset = (
        Evaluation.objects.all()
        .select_related("submission__phase__challenge", "submission__creator")
        .prefetch_related("outputs__interface")
    )
    serializer_class = EvaluationSerializer
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = (DjangoFilterBackend, ViewObjectPermissionsFilter)
    filterset_fields = ["submission__phase"]
    renderer_classes = (
        *api_settings.DEFAULT_RENDERER_CLASSES,
        PaginatedCSVRenderer,
    )

    @action(
        detail=True,
        methods=["PATCH"],
        permission_classes=[CanClaimEvaluation],
        serializer_class=ExternalEvaluationSerializer,
    )
    def claim(self, request, *args, **kwargs):
        evaluation = self.get_object()

        if not evaluation.status == Evaluation.PENDING:
            return Response(
                {"status": "You can only claim pending evaluations."},
                status=400,
            )

        if request.user.claimed_evaluations.exists():
            return Response(
                {"status": "You can only claim one evaluation at a time."},
                status=400,
            )

        serializer = self.get_serializer(
            instance=evaluation, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data)
        else:
            return Response(
                data=serializer.errors, status=HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="submission__phase",
                location=OpenApiParameter.QUERY,
                description="Filter claimable evaluations by submission phase",
                type=OpenApiTypes.UUID,
            ),
        ],
    )
    @action(
        detail=False,
        methods=["GET"],
        filter_backends=[DjangoFilterBackend, CanClaimEvaluationFilter],
        serializer_class=ExternalEvaluationSerializer,
    )
    def claimable_evaluations(self, request, *args, **kwargs):

        qs = self.filter_queryset(self.get_queryset())
        serializer = ExternalEvaluationSerializer(
            qs, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["PATCH"],
        permission_classes=[CanClaimEvaluation],
        serializer_class=ExternalEvaluationUpdateSerializer,
    )
    def update_external_evaluation(self, request, *args, **kwargs):
        evaluation = self.get_object()
        if evaluation.status != Evaluation.CLAIMED:
            return Response(
                {
                    "status": "You need to claim an evaluation before you can update it."
                },
                status=400,
            )

        if request.user != evaluation.claimed_by:
            return Response(
                {
                    "status": "You do not have permission to update this evaluation."
                },
                status=403,
            )

        if (
            evaluation.claimed_at - now()
        ).seconds > settings.EXTERNAL_EVALUATION_TIMEOUT_IN_SECONDS:
            on_commit(cancel_external_evaluations_past_timeout.apply_async)
            return Response(
                {"status": "The evaluation was not updated in time."},
                status=400,
            )

        serializer = self.get_serializer(
            instance=evaluation, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data)
        else:
            return Response(
                data=serializer.errors, status=HTTP_400_BAD_REQUEST
            )
