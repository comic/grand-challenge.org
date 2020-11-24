from functools import reduce
from operator import or_

from django.db.models import Q
from django_filters import (
    CharFilter,
    FilterSet,
    ModelMultipleChoiceFilter,
)
from django_select2.forms import Select2MultipleWidget

from grandchallenge.anatomy.models import BodyRegion
from grandchallenge.challenges.forms import ChallengeFilterForm
from grandchallenge.challenges.models import (
    BodyStructure,
    Challenge,
    ChallengeSeries,
    ImagingModality,
    TaskType,
)


class ChallengeFilter(FilterSet):
    search = CharFilter(method="search_filter", label="Title or Description")
    modalities = ModelMultipleChoiceFilter(
        queryset=ImagingModality.objects.all(),
        widget=Select2MultipleWidget,
        label="Modality",
    )
    task_types = ModelMultipleChoiceFilter(
        queryset=TaskType.objects.all(),
        widget=Select2MultipleWidget,
        label="Task Type",
    )
    structures = ModelMultipleChoiceFilter(
        queryset=BodyStructure.objects.all(),
        widget=Select2MultipleWidget,
        label="Anatomical Structure",
    )
    structures__region = ModelMultipleChoiceFilter(
        queryset=BodyRegion.objects.all(),
        widget=Select2MultipleWidget,
        label="Anatomical Region",
    )
    series = ModelMultipleChoiceFilter(
        queryset=ChallengeSeries.objects.all(),
        widget=Select2MultipleWidget,
        label="Challenge Series",
    )

    class Meta:
        model = Challenge
        fields = (
            "search",
            "series",
            "task_types",
            "modalities",
            "structures",
            "structures__region",
            "educational",
        )
        form = ChallengeFilterForm

    def search_filter(self, queryset, name, value):
        search_fields = [
            "title",
            "short_name",
            "description",
            "event_name",
        ]
        return queryset.filter(
            reduce(
                or_,
                [Q(**{f"{f}__icontains": value}) for f in search_fields],
                Q(),
            )
        )
