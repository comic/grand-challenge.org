import pytest

from grandchallenge.components.models import ComponentInterface
from grandchallenge.core.utils.grand_challenge_forge import (
    get_forge_algorithm_template_context,
    get_forge_challenge_pack_context,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.archives_tests.factories import ArchiveFactory
from tests.components_tests.factories import (
    ComponentInterfaceExampleValueFactory,
    ComponentInterfaceFactory,
)
from tests.evaluation_tests.factories import PhaseFactory
from tests.factories import ChallengeFactory


@pytest.mark.django_db
def test_get_challenge_pack_context():
    challenge = ChallengeFactory()
    inputs = [
        ComponentInterfaceFactory(kind=ComponentInterface.Kind.INTEGER),
        ComponentInterfaceFactory(),
    ]
    outputs = [
        ComponentInterfaceFactory(),
        ComponentInterfaceFactory(),
    ]

    # Add an example
    ComponentInterfaceExampleValueFactory(
        interface=inputs[0],
        value=87,
    )

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

    context = get_forge_challenge_pack_context(challenge)
    assert context["challenge"]["slug"] == challenge.slug

    assert len(context["challenge"]["archives"]) == 1
    for key in ["slug", "url"]:
        assert key in context["challenge"]["archives"][0]

    assert len(context["challenge"]["phases"]) == 2
    for phase in context["challenge"]["phases"]:
        for phase_key in [
            "slug",
            "archive",
            "algorithm_inputs",
            "algorithm_outputs",
        ]:
            assert phase_key in phase
            for ci_key in [
                "slug",
                "kind",
                "super_kind",
                "relative_path",
                "example_value",
            ]:
                for component_interface in [
                    *phase["algorithm_inputs"],
                    *phase["algorithm_outputs"],
                ]:
                    assert ci_key in component_interface

    # Quick check on CI input and outputs
    for index, ci in enumerate(
        context["challenge"]["phases"][0]["algorithm_inputs"]
    ):
        assert inputs[index].slug == ci["slug"]

    # Test assigned example value
    assert (
        context["challenge"]["phases"][0]["algorithm_inputs"][0][
            "example_value"
        ]
        == 87
    )

    for index, ci in enumerate(
        context["challenge"]["phases"][0]["algorithm_outputs"]
    ):
        assert outputs[index].slug == ci["slug"]

    context = get_forge_challenge_pack_context(
        challenge, phase_pks=[phase_1.pk]
    )
    assert len(context["challenge"]["phases"]) == 1

    context = get_forge_challenge_pack_context(
        challenge, phase_pks=[phase_3.pk]
    )
    assert len(context["challenge"]["phases"]) == 0


@pytest.mark.django_db
def test_get_algorithm_template_context():
    algorithm = AlgorithmFactory()

    inputs = [
        ComponentInterfaceFactory(kind=ComponentInterface.Kind.INTEGER),
    ]
    algorithm.inputs.set(inputs)

    outputs = [
        ComponentInterfaceFactory(),
        ComponentInterfaceFactory(),
    ]
    algorithm.outputs.set(outputs)

    context = get_forge_algorithm_template_context(algorithm=algorithm)

    for key in ["title", "url", "inputs", "outputs"]:
        assert key in context["algorithm"]

    for index, ci in enumerate(context["algorithm"]["inputs"]):
        assert inputs[index].slug == ci["slug"]

    for index, ci in enumerate(context["algorithm"]["outputs"]):
        assert outputs[index].slug == ci["slug"]

    # Test adding default examples
    assert context["algorithm"]["inputs"][0]["example_value"] == 42
