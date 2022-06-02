import pytest

from grandchallenge.reader_studies.filters import AnswerFilter
from grandchallenge.reader_studies.models import Answer
from tests.reader_studies_tests.factories import AnswerFactory


@pytest.mark.django_db
def test_answers_filterable_by_ground_truth():
    a, gt = AnswerFactory(is_ground_truth=False), AnswerFactory(
        is_ground_truth=True
    )
    qs = Answer.objects.all()

    f = AnswerFilter(data={}, queryset=qs)
    assert {*f.qs} == {a, gt}

    f = AnswerFilter(data={"is_ground_truth": "true"}, queryset=qs)
    assert {*f.qs} == {gt}

    f = AnswerFilter(data={"is_ground_truth": "false"}, queryset=qs)
    assert {*f.qs} == {a}
