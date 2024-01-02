import pytest

from grandchallenge.core.utils.grand_challenge_forge import (
    get_forge_json_description,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices
from tests.archives_tests.factories import ArchiveFactory
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.evaluation_tests.factories import PhaseFactory
from tests.factories import ChallengeFactory


@pytest.mark.django_db
def test_get_forge_json_description():
    challenge = ChallengeFactory()
    inputs = [
        ComponentInterfaceFactory(),
        ComponentInterfaceFactory(),
    ]
    outputs = [
        ComponentInterfaceFactory(),
        ComponentInterfaceFactory(),
    ]
    archive = ArchiveFactory()
    phase_1 = PhaseFactory(
        challenge=challenge,
        archive=archive,
        submission_kind=SubmissionKindChoices.ALGORITHM,
    )
    phase_2 = PhaseFactory(
        challenge=challenge,
        archive=archive,
        submission_kind=SubmissionKindChoices.ALGORITHM,
    )
    for phase in phase_1, phase_2:
        phase.algorithm_inputs.set(inputs)
        phase.algorithm_outputs.set(outputs)

    # Setup phases that should not pass the filters
    phase_3 = PhaseFactory(
        challenge=challenge,
        archive=None,  # Hence should not be included
        submission_kind=SubmissionKindChoices.ALGORITHM,
    )
    PhaseFactory(
        challenge=challenge,
        submission_kind=SubmissionKindChoices.CSV,  # Hence should not be included
    )

    description = get_forge_json_description(challenge)
    assert description["challenge"]["slug"] == challenge.slug

    assert len(description["challenge"]["archives"]) == 1
    for key in ["slug", "url"]:
        assert key in description["challenge"]["archives"][0]

    assert len(description["challenge"]["phases"]) == 2
    for phase in description["challenge"]["phases"]:
        for phase_key in ["slug", "archive", "inputs", "outputs"]:
            assert phase_key in phase
            for ci_key in ["slug", "kind", "super_kind", "relative_path"]:
                for component_interface in [
                    *phase["inputs"],
                    *phase["outputs"],
                ]:
                    assert ci_key in component_interface

    # Quick check on CI input and outputs
    for index, ci in enumerate(
        description["challenge"]["phases"][0]["inputs"]
    ):
        assert inputs[index].slug == ci["slug"]

    for index, ci in enumerate(
        description["challenge"]["phases"][0]["outputs"]
    ):
        assert outputs[index].slug == ci["slug"]

    description = get_forge_json_description(challenge, phase_pks=[phase_1.pk])
    assert len(description["challenge"]["phases"]) == 1

    description = get_forge_json_description(challenge, phase_pks=[phase_3.pk])
    assert len(description["challenge"]["phases"]) == 0
