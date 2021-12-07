from django_filters import ChoiceFilter, ModelMultipleChoiceFilter
from django_select2.forms import Select2MultipleWidget

from grandchallenge.challenges.models import (
    Challenge,
    ChallengeSeries,
)
from grandchallenge.core.filters import TitleDescriptionModalityStructureFilter
from grandchallenge.evaluation.utils import StatusChoices
from grandchallenge.task_categories.models import TaskType


STATUS_CHOICES = (
    (StatusChoices.OPEN, "Accepting submissions now"),
    (StatusChoices.OPENING_SOON, "Opening submissions soon"),
    (StatusChoices.CLOSED, "Not accepting submissions"),
    (StatusChoices.COMPLETED, "Completed"),
)


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


class InternalChallengeFilter(ChallengeFilter):
    status = ChoiceFilter(
        choices=STATUS_CHOICES,
        method="filter_by_status",
        label="Challenge status",
    )

    def filter_by_status(self, queryset, name, value):
        ids = [
            challenge.id
            for challenge in queryset
            if challenge.status.__str__() == value
        ]
        return queryset.filter(pk__in=ids)
