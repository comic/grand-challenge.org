from rest_framework.serializers import ModelSerializer

from grandchallenge.components.serializers import (
    ComponentInterfaceValueSerializer,
)
from grandchallenge.evaluation.models import AlgorithmEvaluation


class AlgorithmEvaluationSerializer(ModelSerializer):
    inputs = ComponentInterfaceValueSerializer(many=True)
    outputs = ComponentInterfaceValueSerializer(many=True)

    class Meta:
        model = AlgorithmEvaluation
        fields = (
            "pk",
            "inputs",
            "outputs",
        )
