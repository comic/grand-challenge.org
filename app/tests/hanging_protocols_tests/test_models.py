from contextlib import nullcontext

import pytest
from django.core.exceptions import ValidationError
from django.db.models.base import ModelBase

from grandchallenge.hanging_protocols.models import (
    HangingProtocol,
    ViewContentMixin,
)
from tests.factories import UserFactory


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
    ],
)
def test_hanging_protocol_schema_validation(client, json, expectation):
    with expectation:
        hp = HangingProtocol(title="test", creator=UserFactory(), json=json)
        hp.full_clean()


def test_view_content_validation():
    model = ViewContentMixin
    model = ModelBase(
        "__TestModel__" + model.__name__,
        (model,),
        {"__module__": model.__module__},
    )
    with pytest.raises(ValidationError):
        hp = model(view_content={"test": []})
        hp.full_clean()

    with pytest.raises(ValidationError):
        hp = model(view_content={"main": []})
        hp.full_clean()

    with pytest.raises(ValidationError):
        hp = model(view_content={"main": "test"})
        hp.full_clean()

    hp = model(view_content={"main": ["test"]})
    hp.full_clean()
