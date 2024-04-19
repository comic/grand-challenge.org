import pytest

from grandchallenge.evaluation.admin import PhaseAdmin
from grandchallenge.evaluation.utils import SubmissionKindChoices
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.evaluation_tests.factories import PhaseFactory
from tests.factories import ChallengeFactory


@pytest.mark.django_db
def test_disjoint_interfaces():
    i = ComponentInterfaceFactory()
    p = PhaseFactory(challenge=ChallengeFactory())
    form = PhaseAdmin.form(
        instance=p,
        data={"algorithm_inputs": [i.pk], "algorithm_outputs": [i.pk]},
    )
    assert form.is_valid() is False
    assert (
        "The sets of Algorithm Inputs and Algorithm Outputs must be unique"
        in str(form.errors)
    )


@pytest.mark.django_db
def test_read_only_fields_disabled():
    p1, p2 = PhaseFactory.create_batch(
        2,
        submission_kind=SubmissionKindChoices.ALGORITHM,
        challenge=ChallengeFactory(),
    )
    p1.parent = p2
    p1.save()
    form = PhaseAdmin.form(
        instance=p1,
    )
    for field in p1.read_only_fields_for_dependent_phases:
        assert form.fields[field].disabled
