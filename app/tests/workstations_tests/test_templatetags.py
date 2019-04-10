import pytest

from grandchallenge.workstations.templatetags.workstations import (
    update_url,
    workstation_url,
)
from tests.factories import ImageFactory, SessionFactory


@pytest.mark.parametrize(
    "orig_url",
    [
        "https://example.com/#!/?workstation=Basic",
        "https://example.com/?workstation=Basic",
        "https://example.com/?query=here#!/?workstation=Basic",
    ],
)
def test_update_url(orig_url):
    foo_bar = {"foo": "bar"}

    url = update_url(url=orig_url, query=foo_bar)
    assert url == f"{orig_url}&foo=bar"


@pytest.mark.django_db
def test_workstation_url_session(settings):
    image, overlay = ImageFactory(), ImageFactory()
    context = {}

    url = workstation_url(context=context, image=image, overlay=overlay)
    assert url.startswith(settings.WORKSTATIONS_GLOBAL_APPLICATION)
    assert f"{settings.WORKSTATIONS_BASE_IMAGE_QUERY_PARAM}={image.pk}" in url
    assert f"{settings.WORKSTATIONS_OVERLAY_QUERY_PARAM}={overlay.pk}" in url

    session = SessionFactory()
    context = {"workstation_session": session}

    url = workstation_url(context=context, image=image, overlay=overlay)
    assert url.startswith(session.workstation_url)
    assert f"{settings.WORKSTATIONS_BASE_IMAGE_QUERY_PARAM}={image.pk}" in url
    assert f"{settings.WORKSTATIONS_OVERLAY_QUERY_PARAM}={overlay.pk}" in url
