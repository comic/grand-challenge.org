import json

import pytest

from grandchallenge.components.models import (
    ComponentInterface,
    InterfaceKindChoices,
)
from grandchallenge.components.utils import generate_view_content_example
from tests.components_tests.factories import ComponentInterfaceFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "number_of_images, number_of_overlays, expected_example",
    (
        (
            0,
            0,
            None,
        ),
        (
            1,
            0,
            {"main": ["test-ci-image-0"]},
        ),
        (
            0,
            1,
            None,
        ),
        (
            5,
            5,
            {
                "main": ["test-ci-image-0", "test-ci-overlay-0"],
                "secondary": ["test-ci-image-1", "test-ci-overlay-1"],
                "tertiary": ["test-ci-image-2", "test-ci-overlay-2"],
                "quaternary": ["test-ci-image-3", "test-ci-overlay-3"],
                "quinary": ["test-ci-image-4", "test-ci-overlay-4"],
            },
        ),
        (
            6,
            3,
            {
                "main": ["test-ci-image-0", "test-ci-overlay-0"],
                "secondary": ["test-ci-image-1", "test-ci-overlay-1"],
                "tertiary": ["test-ci-image-2", "test-ci-overlay-2"],
                "quaternary": ["test-ci-image-3"],
                "quinary": ["test-ci-image-4"],
                "senary": ["test-ci-image-5"],
            },
        ),
        (
            3,
            6,
            {
                "main": ["test-ci-image-0", "test-ci-overlay-0"],
                "secondary": ["test-ci-image-1", "test-ci-overlay-1"],
                "tertiary": ["test-ci-image-2", "test-ci-overlay-2"],
            },
        ),
    ),
)
@pytest.mark.parametrize(
    "overlay_type",
    (
        InterfaceKindChoices.SEGMENTATION,
        InterfaceKindChoices.HEAT_MAP,
        InterfaceKindChoices.DISPLACEMENT_FIELD,
    ),
)
def test_generate_view_content_example(
    number_of_images, number_of_overlays, expected_example, overlay_type
):

    for i in range(number_of_images):
        ComponentInterfaceFactory(
            kind=InterfaceKindChoices.IMAGE, title=f"test-ci-image-{i}"
        )

    for i in range(number_of_overlays):
        ComponentInterfaceFactory(
            kind=overlay_type,
            title=f"test-ci-overlay-{i}",
        )

    interfaces = ComponentInterface.objects.filter(
        title__startswith="test-ci-"
    ).all()

    view_content_example = generate_view_content_example(interfaces)
    view_content_example_json = (
        json.loads(view_content_example) if view_content_example else None
    )

    assert view_content_example_json == expected_example
