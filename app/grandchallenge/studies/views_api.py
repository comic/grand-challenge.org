from rest_framework.viewsets import ReadOnlyModelViewSet
from grandchallenge.core.utils.query import filter_queryset_fields
from grandchallenge.studies.models import Study
from grandchallenge.studies.serializers import StudySerializer


class StudyViewSet(ReadOnlyModelViewSet):
    serializer_class = StudySerializer

    def get_queryset(self):
        filters = {"patient": self.request.query_params.get("patient", None)}

        return filter_queryset_fields(filters, model=Study)
