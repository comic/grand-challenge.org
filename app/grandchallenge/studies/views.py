from rest_framework.viewsets import ReadOnlyModelViewSet

from grandchallenge.studies.models import Study
from grandchallenge.studies.serializers import StudySerializer


class StudyViewSet(ReadOnlyModelViewSet):
    serializer_class = StudySerializer
    queryset = Study.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()

        if "patient" in self.request.query_params:
            queryset = queryset.filter(
                patient=self.request.query_params["patient"]
            )

        return queryset
