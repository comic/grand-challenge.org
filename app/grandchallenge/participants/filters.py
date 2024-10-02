from django_filters import CharFilter
from django_filters.rest_framework import FilterSet

from grandchallenge.participants.models import (
    RegistrationQuestion,
    RegistrationQuestionAnswer,
)
from grandchallenge.reader_studies.models import Answer, ReaderStudy


class RegistrationQuestionAnswerFilter(FilterSet):
    class Meta:
        model = RegistrationQuestionAnswer
        fields = ("question__challenge__short_name",)
