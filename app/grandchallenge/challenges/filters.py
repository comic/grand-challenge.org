from django_filters import ModelMultipleChoiceFilter
from django_select2.forms import Select2MultipleWidget

from grandchallenge.challenges.models import (
    Challenge,
    ChallengeSeries,
)
from grandchallenge.core.filters import TitleDescriptionModalityStructureFilter
from grandchallenge.task_categories.models import TaskType


class ChallengeFilter(TitleDescriptionModalityStructureFilter):
    task_types = ModelMultipleChoiceFilter(
        queryset=TaskType.objects.all(),
        widget=Select2MultipleWidget,
        label="Task Type",
    )
    series = ModelMultipleChoiceFilter(
        queryset=ChallengeSeries.objects.all(),
        widget=Select2MultipleWidget,
        label="Challenge Series",
    )

    class Meta(TitleDescriptionModalityStructureFilter.Meta):
        model = Challenge
        fields = (
            *TitleDescriptionModalityStructureFilter.Meta.fields,
            "series",
            "task_types",
            "educational",
        )
        search_fields = (
            *TitleDescriptionModalityStructureFilter.Meta.search_fields,
            "short_name",
            "event_name",
        )
