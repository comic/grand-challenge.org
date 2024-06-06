import pytest
from django.template.loader import render_to_string

from grandchallenge.components.models import InterfaceKindChoices
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, ImageFileFactory


@pytest.mark.parametrize(
    "template",
    [
        "components/partials/civ.html",
        "components/partials/civ_inline.html",
    ],
)
@pytest.mark.parametrize(
    "component_interface_value,expected_snippet",
    (
        (
            ComponentInterfaceValueFactory.build(  # Value
                interface=ComponentInterfaceFactory.build(
                    kind=InterfaceKindChoices.FLOAT,
                ),
                value=42,
            ),
            "<pre",
        ),
        (
            ComponentInterfaceValueFactory.build(  # File
                interface=ComponentInterfaceFactory.build(
                    kind=InterfaceKindChoices.PDF,
                ),
                file="file.pdf",
            ),
            "<a ",
        ),
        (
            ComponentInterfaceValueFactory.build(  # Image
                interface=ComponentInterfaceFactory.build(
                    kind=InterfaceKindChoices.IMAGE,
                ),
            ),
            "<a ",
        ),
        (
            ComponentInterfaceValueFactory.build(  # Chart Value
                interface=ComponentInterfaceFactory.build(
                    kind=InterfaceKindChoices.CHART,
                ),
                value={"spec": "A chart, doesn't need to be valid"},
            ),
            "vega-lite-chart",
        ),
        (
            ComponentInterfaceValueFactory.build(  # Thumbnail File
                interface=ComponentInterfaceFactory.build(
                    kind=InterfaceKindChoices.THUMBNAIL_JPG,
                ),
                file="thumbnail.jpg",
            ),
            "<img ",
        ),
        (
            ComponentInterfaceValueFactory.build(  # Fallback
                interface=ComponentInterfaceFactory.build(
                    kind=InterfaceKindChoices.CSV,
                ),
            ),
            "cannot display",
        ),
    ),
)
@pytest.mark.django_db
def test_civ(template, component_interface_value, expected_snippet):
    if component_interface_value.interface.kind == InterfaceKindChoices.IMAGE:
        component_interface_value.image = ImageFactory()
        ImageFileFactory(image=component_interface_value.image)

    html = render_to_string(
        template, context={"object": component_interface_value}
    )
    assert expected_snippet in html
