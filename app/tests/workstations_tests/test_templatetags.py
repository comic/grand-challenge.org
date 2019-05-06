import pytest

from grandchallenge.workstations.templatetags.workstations import (
    workstation_query,
)
from tests.factories import ImageFactory


@pytest.mark.django_db
def test_workstation_query(settings):
    image, overlay = ImageFactory(), ImageFactory()

    qs = workstation_query(image=image)
    assert "&" not in qs
    assert f"{settings.WORKSTATIONS_BASE_IMAGE_QUERY_PARAM}={image.pk}" in qs
    assert (
        f"{settings.WORKSTATIONS_OVERLAY_QUERY_PARAM}={overlay.pk}" not in qs
    )

    qs = workstation_query(image=image, overlay=overlay)
    assert "&" in qs
    assert f"{settings.WORKSTATIONS_BASE_IMAGE_QUERY_PARAM}={image.pk}" in qs
    assert f"{settings.WORKSTATIONS_OVERLAY_QUERY_PARAM}={overlay.pk}" in qs
