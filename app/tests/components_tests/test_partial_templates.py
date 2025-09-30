import pytest
from django.core.files.base import ContentFile
from django.template.loader import render_to_string

from grandchallenge.components.models import InterfaceKindChoices
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, ImageFileFactory


@pytest.mark.parametrize(
    "display_inline",
    [True, False],
)
@pytest.mark.parametrize(
    "component_interface, component_interface_value,expected_snippet",
    (
        (
            dict(  # VALUE
                kind=InterfaceKindChoices.FLOAT,
            ),
            dict(
                value=42,
            ),
            "<pre",
        ),
        (  # VALUE CHART
            dict(
                kind=InterfaceKindChoices.CHART,
            ),
            dict(
                value={
                    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                    "description": "A simple bar chart with embedded data.",
                    "data": {
                        "values": [
                            {"a": "A", "b": 28},
                            {"a": "B", "b": 55},
                        ]
                    },
                    "mark": "bar",
                    "encoding": {
                        "x": {
                            "field": "a",
                            "type": "nominal",
                            "axis": {"labelAngle": 0},
                        },
                        "y": {"field": "b", "type": "quantitative"},
                    },
                },
            ),
            "vega-lite-chart",
        ),
        (
            dict(  # FILE
                kind=InterfaceKindChoices.PDF,
                store_in_database=False,
            ),
            dict(),
            "<a ",
        ),
        (  # FILE Thumbnail
            dict(
                kind=InterfaceKindChoices.THUMBNAIL_JPG,
                store_in_database=False,
            ),
            dict(),
            "<img",
        ),
        (  # MHA_OR_TIFF_IMAGE
            dict(
                kind=InterfaceKindChoices.MHA_OR_TIFF_IMAGE,
                store_in_database=False,
            ),
            dict(),
            "<a ",
        ),
        (  # Broken / fallback
            dict(
                kind=InterfaceKindChoices.SEGMENTATION,
                store_in_database=False,
            ),
            dict(),
            "cannot be displayed",
        ),
    ),
)
@pytest.mark.django_db
def test_civ(
    display_inline,
    component_interface,
    component_interface_value,
    expected_snippet,
):
    ci = ComponentInterfaceFactory(**component_interface)
    civ = ComponentInterfaceValueFactory.build(
        interface=ci, **component_interface_value
    )

    if ci.kind == InterfaceKindChoices.PDF:
        civ.file.save("file.pdf", ContentFile(b"%PDF-1.4\n"))

    if ci.kind == InterfaceKindChoices.THUMBNAIL_JPG:
        civ.file.save(
            "thumbnail.jpg",
            ContentFile(b"<bh:ff><bh:d8><bh:ff><bh:e0><bh:00><bh:10>JFIF"),
        )

    if ci.kind == InterfaceKindChoices.MHA_OR_TIFF_IMAGE:
        civ.image = ImageFactory()
        ImageFileFactory(image=civ.image)

    # Actually create the CIV
    if ci.kind != InterfaceKindChoices.SEGMENTATION:  # Intentionally broken
        civ.full_clean()
    civ.save()

    html = render_to_string(
        "components/partials/civ.html",
        context={
            "object": civ,
            "display_inline": display_inline,
        },
    )
    assert expected_snippet in html
