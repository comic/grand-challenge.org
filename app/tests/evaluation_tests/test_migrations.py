import pytest
from django.core.management import call_command

from grandchallenge.evaluation.models import Result
from tests.factories import JobFactory


@pytest.mark.django_db
def test_evaluation_results_migration():
    j1, j2 = JobFactory(), JobFactory()

    Result.objects.create(
        metrics={"a": 42}, published=True, job=j1,
    )
    Result.objects.create(
        metrics={"b": 3.14159}, published=False, job=j2,
    )

    assert len(j1.outputs.all()) == 0
    assert j1.published is True
    assert j1.rank == 0

    assert len(j2.outputs.all()) == 0
    assert j2.published is True
    assert j2.rank == 0

    call_command("migrate_evaluation_results")

    j1.refresh_from_db()
    j2.refresh_from_db()

    assert j1.outputs.get(interface__slug="metrics-json-file").value == {
        "a": 42
    }
    assert j1.published is True
    assert j1.rank == 0

    assert j2.outputs.get(interface__slug="metrics-json-file").value == {
        "b": 3.14159
    }
    assert j2.published is False
    assert j2.rank == 0
