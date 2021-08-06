from django_filters import CharFilter
from django_filters.rest_framework import FilterSet

from grandchallenge.core.filters import TitleDescriptionModalityStructureFilter
from grandchallenge.reader_studies.models import Answer, ReaderStudy


class ReaderStudyFilter(TitleDescriptionModalityStructureFilter):
    class Meta(TitleDescriptionModalityStructureFilter.Meta):
        model = ReaderStudy


class AnswerFilter(FilterSet):
    creator = CharFilter(field_name="creator__username", label="username")

    class Meta:
        model = Answer
        fields = ("creator", "question__reader_study")
