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
    assert form.fields["algorithm_inputs"].disabled
    assert form.fields["algorithm_outputs"].disabled
    assert form.fields["submission_kind"].disabled

    p3, p4 = PhaseFactory.create_batch(
        2,
        submission_kind=SubmissionKindChoices.CSV,
        challenge=ChallengeFactory(),
    )
    p3.parent = p4
    p3.save()
    form = PhaseAdmin.form(
        instance=p3,
    )
    assert form.fields["submission_kind"].disabled


@pytest.mark.django_db
def test_selectable_gpu_type_choices_invalid():
    phase = PhaseFactory()
    form = PhaseAdmin.form(
        instance=phase,
        data={"evaluation_selectable_gpu_type_choices": '["invalid_choice"]'},
    )

    assert form.is_valid() is False
    assert (
        "JSON does not fulfill schema: instance &#x27;invalid_choice&#x27; is not "
        "one of " in str(form.errors)
    )
