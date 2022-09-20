import pytest
from celery.result import AsyncResult
from django.core.management import CommandError, call_command
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.components.models import InterfaceKind
from tests.cases_tests.factories import ImageFactoryWithImageFile16Bit
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)


@pytest.mark.django_db
def test_add_overlay_segments(settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    im = ImageFactoryWithImageFile16Bit()
    ci = ComponentInterfaceFactory(
        title="foo", kind=InterfaceKind.InterfaceKindChoices.SEGMENTATION
    )
    ComponentInterfaceValueFactory(interface=ci, image=im)

    im.segments = [2]
    im.save()

    with pytest.raises(CommandError) as e:
        call_command("add_overlay_segments", "non-existent", '{"255": "seg"}')

    assert str(e.value) == "Could not find interface with slug: non-existent."

    # This raises a ValidationError, but unfortunetaly that gest swallowed in
    # the context manager.
    with capture_on_commit_callbacks() as callbacks:
        call_command("add_overlay_segments", "foo", '{"255": "seg"}')

    error = (
        "The valid voxel values for this segmentation are: {0, 255}. "
        "This segmentation is invalid as it contains the voxel values: {2}."
    )

    for callback in callbacks:
        maybe_task = callback()
        if isinstance(maybe_task, AsyncResult):
            assert error in maybe_task.traceback

    ci.refresh_from_db()
    assert ci.overlay_segments == [
        {"name": "seg", "voxel_value": 255, "visible": True}
    ]

    im.segments = None
    im.save()
    with capture_on_commit_callbacks(execute=True):
        call_command("add_overlay_segments", "foo", '{"255": "seg"}')
    im.refresh_from_db()
    assert im.segments == [0]
