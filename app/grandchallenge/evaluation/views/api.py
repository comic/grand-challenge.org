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

from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.components.serializers import (
    ComponentInterfaceValuePostSerializer,
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
        evaluation.claimed_at = now()
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
        outputs = request.data.pop("outputs", None)
        if outputs:
            serialized_data = ComponentInterfaceValuePostSerializer(
                many=True, data=outputs, context={"request": request}
            )
            if serialized_data.is_valid():
                for value in serialized_data.validated_data:
                    # minimal implementation until we can use
                    # CIVForObjectMixin on the evaluation model
                    # (pending algorithm job refactoring)
                    interface = value.get("interface", None)
                    if not interface.is_json_kind:
                        raise DRFValidationError(
                            "Evaluation outputs can only be json data."
                        )
                    value = value.get("value", None)
                    civ = ComponentInterfaceValue(
                        interface=interface, value=value
                    )
                    try:
                        civ.full_clean()
                        civ.save()
                        evaluation.outputs.add(civ)
                    except ValidationError as e:
                        evaluation.status = Evaluation.FAILURE
                        evaluation.save()
                        raise DRFValidationError(e)
            else:
                evaluation.status = Evaluation.FAILURE
                evaluation.save()
                raise DRFValidationError(serialized_data.errors)

        evaluation.status = Evaluation.SUCCESS
        evaluation.completed_at = now()
        evaluation.save()
        # return the serialized updated evaluation object,
        # we're using the normal serializer not the POST serializer
        serialized_evaluation = ExternalEvaluationSerializer(
            instance=evaluation, context={"request": request}
        )
        return Response(serialized_evaluation.data)
