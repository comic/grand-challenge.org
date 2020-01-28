from urllib.parse import urljoin

import pytest
from favicon.models import Favicon

from grandchallenge.core.management.commands.init_gc_demo import (
    get_temporary_image,
)
from tests.factories import ChallengeFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    ["/favicon.ico", "/apple-touch-icon.png", "/apple-touch-icon-240x240.png"],
)
def test_get_favicon_redirect(client, path):
    response = get_view_for_user(client=client, url=path)
    assert response.status_code == 404

    Favicon.objects.create(title="favicon", faviconImage=get_temporary_image())

    response = get_view_for_user(client=client, url=path)
    assert response.status_code == 302
    assert "grand-challenge-public" in response.url

    c = ChallengeFactory()

    response = get_view_for_user(
        client=client, url=urljoin(c.get_absolute_url(), path)
    )
    assert response.status_code == 302
    assert "grand-challenge-public" in response.url
