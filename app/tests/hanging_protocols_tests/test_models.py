from contextlib import nullcontext

import pytest
from django.core.exceptions import ValidationError
from django.db.models.base import Model

from grandchallenge.components.models import InterfaceKindChoices
from grandchallenge.hanging_protocols.models import (
    HangingProtocol,
    HangingProtocolMixin,
)
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.factories import UserFactory
from tests.hanging_protocols_tests.factories import HangingProtocolFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "json,expectation",
    [
        # valid json with two viewports
        (
            [
                {
                    "viewport_name": "main",
                    "x": 0,
                    "y": 0,
                    "w": 1,
                    "h": 1,
                    "fullsizable": True,
                    "draggable": False,
                    "selectable": True,
                    "order": 0,
                },
                {
                    "viewport_name": "secondary",
                    "x": 1,
                    "y": 0,
                    "w": 1,
                    "h": 1,
                    "fullsizable": True,
                    "draggable": False,
                    "selectable": True,
                    "order": 1,
                },
            ],
            nullcontext(),
        ),
        # valid json with one viewport
        (
            [
                {
                    "viewport_name": "main",
                    "x": 0,
                    "y": 0,
                    "w": 1,
                    "h": 1,
                    "fullsizable": True,
                    "draggable": False,
                    "selectable": True,
                    "linkable": True,
                    "order": 0,
                    "show_current_slice": True,
                    "show_mouse_coordinate": True,
                    "show_mouse_voxel_value": True,
                    "relative_start_position": 0.5,
                    "label": "Test label",
                    "opacity": 0.5,
                }
            ],
            nullcontext(),
        ),
        # valid json with only the viewport defined,
        # none of the other properties are required
        (
            [
                {
                    "viewport_name": "main",
                }
            ],
            nullcontext(),
        ),
        # valid specialized view: minimap
        (
            [
                {
                    "viewport_name": "main",
                },
                {
                    "viewport_name": "main_minimap",
                    "specialized_view": "minimap",
                    "parent_id": "main",
                },
            ],
            nullcontext(),
        ),
        #  valid specialized view: multiple minimaps
        (
            [
                {
                    "viewport_name": "main",
                },
                {
                    "viewport_name": "main_minimap1",
                    "specialized_view": "minimap",
                    "parent_id": "main",
                },
                {
                    "viewport_name": "main_minimap2",
                    "specialized_view": "minimap",
                    "parent_id": "main",
                },
            ],
            nullcontext(),
        ),
        # valid specialized view: 3D-sideview
        (
            [
                {
                    "viewport_name": "main",
                },
                {
                    "viewport_name": "main_sideview",
                    "specialized_view": "3D-sideview",
                    "slice_plane_indicator": "main",
                    "slice_plane_indicator_fade_ms": 0,
                    "parent_id": "main",
                    "orientation": "axial",
                },
            ],
            nullcontext(),
        ),
        # valid specialized view: multiple 3D-sideview
        (
            [
                {
                    "viewport_name": "main",
                },
                {
                    "viewport_name": "main_sideview_axial",
                    "specialized_view": "3D-sideview",
                    "parent_id": "main",
                    "orientation": "axial",
                },
                {
                    "viewport_name": "main_sideview_coronal",
                    "specialized_view": "3D-sideview",
                    "parent_id": "main",
                    "orientation": "coronal",
                },
            ],
            nullcontext(),
        ),
        # valid mixed specialized views: minimap and 3D-sideview
        (
            [
                {
                    "viewport_name": "main",
                },
                {
                    "viewport_name": "main_minimap",
                    "specialized_view": "minimap",
                    "parent_id": "main",
                },
                {
                    "viewport_name": "main_sideview",
                    "specialized_view": "3D-sideview",
                    "parent_id": "main",
                    "orientation": "axial",
                },
            ],
            nullcontext(),
        ),
        # valid specialized view: intensity-over-time-chart
        (
            [
                {
                    "viewport_name": "main",
                },
                {
                    "viewport_name": "secondary",
                    "specialized_view": "intensity-over-time-chart",
                    "parent_id": "main",
                },
            ],
            nullcontext(),
        ),
        # All valid orientations
        *[
            (
                [
                    {
                        "viewport_name": "main",
                        "orientation": orientation,
                    }
                ],
                nullcontext(),
            )
            for orientation in ["axial", "coronal", "sagittal"]
        ],
        # invalid json missing the main viewport
        (
            [
                {
                    "viewport_name": "secondary",
                    "x": 0,
                    "y": 0,
                    "w": 1,
                    "h": 1,
                    "fullsizable": True,
                    "draggable": False,
                    "selectable": True,
                    "order": 0,
                }
            ],
            pytest.raises(ValidationError),
        ),
        # invalid json missing the viewport property entirely
        (
            [
                {
                    "x": 0,
                    "y": 0,
                    "w": 1,
                    "h": 1,
                    "fullsizable": True,
                    "draggable": False,
                    "selectable": True,
                    "order": 0,
                }
            ],
            pytest.raises(ValidationError),
        ),
        # invalid json with duplicate viewports
        (
            [
                {
                    "viewport_name": "main",
                },
                {
                    "viewport_name": "main",
                },
            ],
            pytest.raises(ValidationError),
        ),
        # invalid json containing an invalid value for
        (
            [
                {
                    "viewport_name": "main",
                },
                {
                    "viewport_name": "secondary",
                    "slice_plane_indicator_fade_ms": -1,
                },
            ],
            pytest.raises(ValidationError),
        ),
        # invalid json containing undefined additional properties
        (
            [
                {
                    "viewport_name": "main",
                    "undefined_property": 0,
                }
            ],
            pytest.raises(ValidationError),
        ),
        # invalid json containing opacity < 0
        (
            [
                {
                    "viewport_name": "main",
                    "opacity": -0.1,
                }
            ],
            pytest.raises(ValidationError),
        ),
        # invalid json containing opacity > 1.0
        (
            [
                {
                    "viewport_name": "main",
                    "opacity": 1.1,
                }
            ],
            pytest.raises(ValidationError),
        ),
        # invalid json containing non viewport name parent_id
        (
            [
                {
                    "viewport_name": "main",
                    "parent_id": "invalid",
                }
            ],
            pytest.raises(ValidationError),
        ),
        # invalid json containing slice_plane_indicator that is not a viewitem name
        (
            [
                {
                    "viewport_name": "main",
                    "slice_plane_indicator": "invalid",
                }
            ],
            pytest.raises(ValidationError),
        ),
        # invalid view port name that is not a valid instance name for MeVisLab module ([a-zA-Z0-9_]+):
        (
            [
                {
                    "viewport_name": "main",
                },
                {
                    "viewport_name": "main-!@#$%^&*()_+",
                    "specialized_view": "minimap",
                    "parent_id": "main",
                },
            ],
            pytest.raises(ValidationError),
        ),
        # invalid specialized view: 3D-sideview misses parent_id
        (
            [
                {
                    "viewport_name": "main",
                },
                {
                    "viewport_name": "main_minimap",
                    "specialized_view": "minimap",
                },
            ],
            pytest.raises(ValidationError),
        ),
        # invalid specialized view: 3D-sideview misses parent_id
        (
            [
                {
                    "viewport_name": "main",
                },
                {
                    "viewport_name": "main_minimap",
                    "specialized_view": "3D-sideview",
                    "orientation": "axial",
                },
            ],
            pytest.raises(ValidationError),
        ),
        # invalid specialized view: intensity-over-time-chart misses parent_id
        (
            [
                {
                    "viewport_name": "main",
                },
                {
                    "viewport_name": "secondary",
                    "specialized_view": "intensity-over-time-chart",
                },
            ],
            pytest.raises(ValidationError),
        ),
        # invalid specialized view: intensity-over-time-chart has invalid parent_id
        (
            [
                {
                    "viewport_name": "main",
                },
                {
                    "viewport_name": "secondary",
                    "specialized_view": "intensity-over-time-chart",
                    "parent_id": "invalid",
                },
            ],
            pytest.raises(ValidationError),
        ),
        # invalid specialized view: 3D-sideview misses orientation
        (
            [
                {
                    "viewport_name": "main",
                },
                {
                    "viewport_name": "main_minimap",
                    "specialized_view": "3D-sideview",
                    "parent_id": "main",
                },
            ],
            pytest.raises(ValidationError),
        ),
        # invalid specialized view: parent is specialized view
        (
            [
                {
                    "viewport_name": "main",
                },
                {
                    "viewport_name": "main_minimap1",
                    "specialized_view": "3D-sideview",
                    "parent_id": "main",
                },
                {
                    "viewport_name": "main_minimap2",
                    "specialized_view": "minimap",
                    "parent_id": "main_minimap1",
                },
            ],
            pytest.raises(ValidationError),
        ),
        # invalid specialized view: repeated viewport names
        (
            [
                {
                    "viewport_name": "main",
                },
                {
                    "viewport_name": "main_minimap1",
                    "specialized_view": "3D-sideview",
                    "parent_id": "main",
                },
                {
                    "viewport_name": "main_minimap1",
                    "specialized_view": "minimap",
                    "parent_id": "main",
                },
            ],
            pytest.raises(ValidationError),
        ),
        # valid json containing relative_start_position
        (
            [
                {
                    "viewport_name": "main",
                    "relative_start_position": 0.5,
                }
            ],
            nullcontext(),
        ),
        # invalid json containing relative_start_position > 1
        (
            [
                {
                    "viewport_name": "main",
                    "relative_start_position": 1.5,
                }
            ],
            pytest.raises(ValidationError),
        ),
        # invalid json containing relative_start_position < 0
        (
            [
                {
                    "viewport_name": "main",
                    "relative_start_position": -1.5,
                }
            ],
            pytest.raises(ValidationError),
        ),
    ],
)
def test_hanging_protocol_schema_validation(client, json, expectation):
    with expectation:
        hp = HangingProtocol(title="test", creator=UserFactory(), json=json)
        hp.full_clean()


class HangingProtocolTestModel(HangingProtocolMixin, Model):
    class Meta:
        app_label = "hanging_protocols_tests"


@pytest.mark.django_db
def test_view_content_validation():
    hp = HangingProtocolTestModel(view_content={"test": []})

    with pytest.raises(ValidationError) as err:
        hp.full_clean()

    assert "JSON does not fulfill schema" in str(err.value)

    hp = HangingProtocolTestModel(view_content={"main": []})

    with pytest.raises(ValidationError) as err:
        hp.full_clean()

    assert "JSON does not fulfill schema" in str(err.value)

    hp = HangingProtocolTestModel(view_content={"main": "test"})

    with pytest.raises(ValidationError) as err:
        hp.full_clean()

    assert "JSON does not fulfill schema" in str(err.value)

    hp = HangingProtocolTestModel(view_content={"main": ["test"]})

    with pytest.raises(ValidationError) as err:
        hp.full_clean()

    assert "Unknown sockets in view content for viewport main: test" in str(
        err.value
    )

    ComponentInterfaceFactory(title="Test", kind=InterfaceKindChoices.STRING)

    hp = HangingProtocolTestModel(view_content={"main": ["test"]})
    hp.full_clean()


@pytest.mark.django_db
def test_at_most_two_images():
    image = ComponentInterfaceFactory(kind=InterfaceKindChoices.IMAGE)
    image2 = ComponentInterfaceFactory(kind=InterfaceKindChoices.IMAGE)
    heatmap = ComponentInterfaceFactory(kind=InterfaceKindChoices.HEAT_MAP)
    segmentation = ComponentInterfaceFactory(
        kind=InterfaceKindChoices.SEGMENTATION
    )
    text = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)

    hp = HangingProtocolTestModel(view_content={"main": [image.slug]})
    hp.full_clean()

    hp = HangingProtocolTestModel(view_content={"main": [heatmap.slug]})
    hp.full_clean()

    hp = HangingProtocolTestModel(
        view_content={"main": [image.slug, heatmap.slug]}
    )
    hp.full_clean()

    hp = HangingProtocolTestModel(
        view_content={"main": [image.slug, heatmap.slug, text.slug]}
    )
    hp.full_clean()

    hp = HangingProtocolTestModel(
        view_content={"main": [image.slug, segmentation.slug]}
    )
    hp.full_clean()

    hp = HangingProtocolTestModel(
        view_content={"main": [image.slug, heatmap.slug, segmentation.slug]}
    )
    hp.full_clean()

    hp = HangingProtocolTestModel(
        view_content={
            "main": [image.slug, image2.slug, heatmap.slug, segmentation.slug]
        }
    )

    with pytest.raises(ValidationError) as err:
        hp.full_clean()

    assert (
        "Maximum of one image socket is allowed per viewport, got 2 for viewport main:"
        in str(err.value)
    )


@pytest.mark.parametrize(
    "interface_kind",
    [
        InterfaceKindChoices.CHART,
        InterfaceKindChoices.PDF,
        InterfaceKindChoices.MP4,
        InterfaceKindChoices.THUMBNAIL_JPG,
        InterfaceKindChoices.THUMBNAIL_PNG,
    ],
)
@pytest.mark.django_db
def test_interfaces_that_must_be_isolated(interface_kind):
    interface, second = ComponentInterfaceFactory.create_batch(
        2, kind=interface_kind
    )
    text = ComponentInterfaceFactory(kind=InterfaceKindChoices.STRING)

    hp = HangingProtocolTestModel(view_content={"main": [interface.slug]})
    hp.full_clean()

    hp = HangingProtocolTestModel(
        view_content={"main": [interface.slug], "secondary": [second.slug]}
    )
    hp.full_clean()

    hp = HangingProtocolTestModel(
        view_content={"main": [interface.slug, second.slug]}
    )

    with pytest.raises(ValidationError) as err:
        hp.full_clean()

    assert (
        "Some of the selected sockets can only be displayed in isolation, found 2 for viewport main"
        in str(err.value)
    )

    hp = HangingProtocolTestModel(
        view_content={"main": [interface.slug, text.slug]}
    )

    with pytest.raises(ValidationError) as err:
        hp.full_clean()

    assert (
        "Some of the selected sockets can only be displayed in isolation, found 1 for viewport main"
        in str(err.value)
    )


@pytest.mark.parametrize(
    "interface_kind",
    [
        InterfaceKindChoices.CSV,
        InterfaceKindChoices.ZIP,
        InterfaceKindChoices.OBJ,
    ],
)
@pytest.mark.django_db
def test_interfaces_that_cannot_be_displayed(interface_kind):
    interface = ComponentInterfaceFactory(kind=interface_kind)
    hp = HangingProtocolTestModel(view_content={"main": [interface.slug]})

    with pytest.raises(ValidationError) as err:
        hp.full_clean()

    assert (
        "Some of the selected sockets cannot be displayed, found 1 for viewport main:"
        in str(err.value)
    )


@pytest.mark.parametrize(
    "json,svg",
    (
        (
            [{"viewport_name": "main"}],
            """<svg width="32" height="18" fill-opacity="0"><rect x="0.8" y="0.8" width="30.4" height="16.4" stroke-width="1.6" /></svg>""",
        ),
        (
            [{"viewport_name": "main"}, {"viewport_name": "secondary"}],
            """<svg width="32" height="18" fill-opacity="0"><rect x="0.8" y="0.8" width="15.2" height="16.4" stroke-width="1.6" /><rect x="16.0" y="0.8" width="15.2" height="16.4" stroke-width="1.6" /></svg>""",
        ),
        (
            [
                {"h": 4, "w": 4, "x": 0, "y": 0, "viewport_name": "main"},
                {"h": 1, "w": 1, "x": 3, "y": 3, "viewport_name": "secondary"},
                {"h": 4, "w": 4, "x": 4, "y": 0, "viewport_name": "tertiary"},
                {
                    "h": 2,
                    "w": 2,
                    "x": 6,
                    "y": 2,
                    "viewport_name": "quaternary",
                },
            ],
            """<svg width="32" height="18" fill-opacity="0"><rect x="0.8" y="0.8" width="15.2" height="16.4" stroke-width="1.6" /><rect x="12.2" y="13.1" width="3.8" height="4.1" stroke-width="1.6" /><rect x="16.0" y="0.8" width="15.2" height="16.4" stroke-width="1.6" /><rect x="23.599999999999998" y="9.0" width="7.6" height="8.2" stroke-width="1.6" /></svg>""",
        ),
    ),
)
def test_hanging_protocol_svg(json, svg):
    hp = HangingProtocolFactory.build(json=json)
    assert hp.svg_icon == svg
