import pytest

from grandchallenge.components.models import ComponentInterface
from grandchallenge.core.utils.grand_challenge_forge import (
    get_forge_algorithm_template_context,
    get_forge_challenge_pack_context,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmInterfaceFactory,
)
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
        ComponentInterfaceFactory(),
    ]
    interface1 = AlgorithmInterfaceFactory(
        inputs=[inputs[0]], outputs=outputs[:2]
    )
    interface2 = AlgorithmInterfaceFactory(
        inputs=[inputs[1]], outputs=[outputs[2]]
    )

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
        phase.algorithm_interfaces.set([interface1, interface2])

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

    # Test assigned example value
    example_values = {
        input["example_value"]
        for input in context["challenge"]["phases"][0]["algorithm_inputs"]
        if input["example_value"]
    }
    assert example_values == {87}

    # Quick check on CI input and outputs
    input_slugs = [
        input["slug"]
        for input in context["challenge"]["phases"][0]["algorithm_inputs"]
    ]
    assert len(input_slugs) == len(inputs)
    assert inputs[0].slug in input_slugs
    assert inputs[1].slug in input_slugs

    output_slugs = [
        output["slug"]
        for output in context["challenge"]["phases"][0]["algorithm_outputs"]
    ]
    assert len(output_slugs) == len(outputs)
    assert outputs[0].slug in output_slugs
    assert outputs[1].slug in output_slugs
    assert outputs[2].slug in output_slugs

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
        ComponentInterfaceFactory(kind=ComponentInterface.Kind.STRING),
    ]
    outputs = [
        ComponentInterfaceFactory(),
        ComponentInterfaceFactory(),
        ComponentInterfaceFactory(),
    ]
    interface1 = AlgorithmInterfaceFactory(
        inputs=[inputs[0]], outputs=outputs[:2]
    )
    interface2 = AlgorithmInterfaceFactory(
        inputs=[inputs[1]], outputs=[outputs[2]]
    )
    algorithm.interfaces.set([interface1, interface2])

    context = get_forge_algorithm_template_context(algorithm=algorithm)

    for key in ["title", "slug", "url", "inputs", "outputs"]:
        assert key in context["algorithm"]

    input_slugs = [input["slug"] for input in context["algorithm"]["inputs"]]
    assert len(input_slugs) == len(inputs)
    assert inputs[0].slug in input_slugs
    assert inputs[1].slug in input_slugs

    output_slugs = [
        output["slug"] for output in context["algorithm"]["outputs"]
    ]
    assert len(output_slugs) == len(outputs)
    assert outputs[0].slug in output_slugs
    assert outputs[1].slug in output_slugs

    # Test adding default examples
    assert context["algorithm"]["inputs"][0]["example_value"] == 42
