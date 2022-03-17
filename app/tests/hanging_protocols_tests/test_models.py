from contextlib import nullcontext

import pytest
from django.core.exceptions import ValidationError

from grandchallenge.hanging_protocols.models import HangingProtocol
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
    ],
)
def test_hanging_protocol_schema_validation(client, json, expectation):
    with expectation:
        hp = HangingProtocol(title="test", creator=UserFactory(), json=json)
        hp.full_clean()
