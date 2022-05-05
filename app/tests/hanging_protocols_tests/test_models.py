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
