import pytest

from grandchallenge.evaluation.admin import PhaseAdmin
from grandchallenge.evaluation.utils import SubmissionKindChoices
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.factories import ChallengeFactory


@pytest.mark.django_db
def test_disjoint_interfaces():
    i = ComponentInterfaceFactory()
    form = PhaseAdmin.form(
        data={"algorithm_inputs": [i.pk], "algorithm_outputs": [i.pk]}
    )
    assert form.is_valid() is False
    assert (
        "The sets of Algorithm Inputs and Algorithm Outputs must be unique"
        in str(form.errors)
    )


@pytest.mark.django_db
def test_total_submission_limit(challenge_request):
    form = PhaseAdmin.form(
        data={"submission_kind": SubmissionKindChoices.ALGORITHM}
    )
    assert not form.is_valid()
    assert (
        "For phases that take an algorithm as submission input, the total_number_of_submissions_allowed needs to be set. There is no corresponding challenge request."
        in str(form.errors)
    )

    ch = ChallengeFactory(short_name=challenge_request.short_name)
    phase = ch.phase_set.first()

    form = PhaseAdmin.form(
        instance=phase,
        data={"submission_kind": SubmissionKindChoices.ALGORITHM},
    )
    assert not form.is_valid()
    assert (
        "For phases that take an algorithm as submission input, the total_number_of_submissions_allowed needs to be set. The corresponding challenge request lists the following limits: Preliminary phase: 100 Final test phase: 0"
        in str(form.errors)
    )

    form = PhaseAdmin.form(
        instance=phase,
        data={
            "submission_kind": SubmissionKindChoices.ALGORITHM,
            "total_number_of_submissions_allowed": 10,
        },
    )
    assert "total_number_of_submissions_allowed" not in form.errors
