from rest_framework.viewsets import ReadOnlyModelViewSet

from grandchallenge.patients.models import Patient
from grandchallenge.patients.serializers import PatientSerializer


class PatientViewSet(ReadOnlyModelViewSet):
    serializer_class = PatientSerializer
    queryset = Patient.objects.all()

    def get_queryset(self):
        filters = {
            "study__image__worklist": self.request.query_params.get(
                "worklist", None
            ),
            "study__image__files__image_type": self.request.query_params.get(
                "image_type", None
            ),
        }
        filters = {k: v for k, v in filters.items() if v is not None}

        queryset = super().get_queryset().filter(**filters).distinct()

        return queryset
