from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.core.guardian import get_objects_for_user
from grandchallenge.core.renderers import PaginatedCSVRenderer
from grandchallenge.evaluation.models import Evaluation
from grandchallenge.evaluation.serializers import (
    EvaluationSerializer,
    ExternalEvaluationSerializer,
    ExternalEvaluationUpdateSerializer,
)


class CanClaimEvaluation(permissions.BasePermission):
    """Object-level permission to only a user with 'claim_evaluation' permission"""

    def has_object_permission(self, request, view, obj):
        return request.user.has_perm("evaluation.claim_evaluation", obj)


class EvaluationViewSet(ReadOnlyModelViewSet):
    queryset = (
        Evaluation.objects.all()
        .select_related("submission__phase__challenge", "submission__creator")
        .prefetch_related("outputs__interface")
    )
    serializer_class = EvaluationSerializer
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = (DjangoFilterBackend, ObjectPermissionsFilter)
    filterset_fields = ["submission__phase"]
    renderer_classes = (
        *api_settings.DEFAULT_RENDERER_CLASSES,
        PaginatedCSVRenderer,
    )

    @action(detail=True, permission_classes=[CanClaimEvaluation])
    def claim(self, request, *args, **kwargs):
        evaluation = self.get_object()

        if not evaluation.status == Evaluation.PENDING:
            return Response(
                {"status": "You can only claim pending evaluations."},
                status=400,
            )

        evaluation.status = Evaluation.EXECUTING
        evaluation.started_at = now()
        evaluation.save()

        serializer = ExternalEvaluationSerializer(
            instance=evaluation, context={"request": request}
        )
        return Response(serializer.data)

    @action(detail=False, methods=["GET"])
    def claimable_evaluations(self, request, *args, **kwargs):
        queryset = get_objects_for_user(
            request.user, "evaluation.claim_evaluation"
        ).filter(status=Evaluation.PENDING)
        serializer = ExternalEvaluationSerializer(
            queryset, many=True, context={"request": request}
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
        if evaluation.status != Evaluation.EXECUTING:
            return Response(
                {
                    "status": "You need to claim an evaluation before you can update it."
                },
                status=400,
            )

        serialized_evaluation = ExternalEvaluationUpdateSerializer(
            instance=evaluation,
            data=request.data,
            context={"request": request},
        )
        if not serialized_evaluation.is_valid():
            raise DRFValidationError(serialized_evaluation.errors)

        status = request.data.get("status", None)

        if status == Evaluation.SUCCESS:
            metrics = request.data.pop("metrics", None)
            interface = ComponentInterface.objects.get(
                slug="metrics-json-file"
            )

            civ = ComponentInterfaceValue(interface=interface, value=metrics)
            try:
                civ.full_clean()
                civ.save()
                evaluation.outputs.add(civ)
                evaluation.status = Evaluation.SUCCESS
            except ValidationError as e:
                evaluation.status = Evaluation.FAILURE
                evaluation.error_message = str(e)
                evaluation.save()
                raise DRFValidationError(e)
        else:
            evaluation.status = Evaluation.FAILURE
            evaluation.error_message = request.data.get("error_message", None)

        evaluation.completed_at = now()
        evaluation.save()

        return Response(
            EvaluationSerializer(
                instance=evaluation, context={"request": request}
            ).data
        )
