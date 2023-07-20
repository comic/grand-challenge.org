from django_filters import BooleanFilter, CharFilter
from django_filters.rest_framework import FilterSet

from grandchallenge.core.filters import TitleDescriptionModalityStructureFilter
from grandchallenge.reader_studies.models import Answer, ReaderStudy


class ReaderStudyFilter(TitleDescriptionModalityStructureFilter):
    public = BooleanFilter(label="Public", field_name="public")

    class Meta(TitleDescriptionModalityStructureFilter.Meta):
        model = ReaderStudy
        search_fields = (
            *TitleDescriptionModalityStructureFilter.Meta.search_fields,
            "public",
        )


class AnswerFilter(FilterSet):
    creator = CharFilter(field_name="creator__username", label="username")

    class Meta:
        model = Answer
        fields = (
            "creator",
            "question__reader_study",
            "display_set",
            "is_ground_truth",
        )
