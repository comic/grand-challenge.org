import pytest

from grandchallenge.components.models import InterfaceKindChoices
from grandchallenge.core.templatetags.civ import civ, civ_inline
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, ImageFileFactory


@pytest.mark.parametrize("tag", [civ, civ_inline])
@pytest.mark.parametrize(
    "component_interface_value",
    (
        ComponentInterfaceValueFactory.build(  # Value
            interface=ComponentInterfaceFactory.build(
                kind=InterfaceKindChoices.FLOAT,
            ),
            value=42,
        ),
        ComponentInterfaceValueFactory.build(  # File
            interface=ComponentInterfaceFactory.build(
                kind=InterfaceKindChoices.FLOAT,
            ),
            file="float.json",
        ),
        ComponentInterfaceValueFactory.build(  # Image
            interface=ComponentInterfaceFactory.build(
                kind=InterfaceKindChoices.IMAGE,
            ),
        ),
        ComponentInterfaceValueFactory.build(  # Chart Value
            interface=ComponentInterfaceFactory.build(
                kind=InterfaceKindChoices.CHART,
            ),
            value={"spec": "A chart, doesn't need to be valid"},
        ),
        ComponentInterfaceValueFactory.build(  # Thumbnail File
            interface=ComponentInterfaceFactory.build(
                kind=InterfaceKindChoices.THUMBNAIL_JPG,
            ),
            file="thumbnail.jpg",
        ),
        ComponentInterfaceValueFactory.build(  # Fallback
            interface=ComponentInterfaceFactory.build(
                kind=InterfaceKindChoices.ANY,
            ),
        ),
    ),
)
@pytest.mark.django_db
def test_civ_render_tag(tag, component_interface_value):
    if component_interface_value.interface.kind != InterfaceKindChoices.IMAGE:
        component_interface_value.image = ImageFactory()
        ImageFileFactory(image=component_interface_value.image)

    assert tag(component_interface_value)
