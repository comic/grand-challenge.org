import uuid

import pytest
from django.core.cache import cache

from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_get_statistics(client, settings):
    settings.STATISTICS_SITE_CACHE_KEY = f"tests/statistics/{uuid.uuid4()}"

    assert cache.get(settings.STATISTICS_SITE_CACHE_KEY) is None

    n_dutch = 3
    for _ in range(n_dutch):
        u = UserFactory()
        u.user_profile.country = "NL"
        u.user_profile.save()

    response = get_view_for_user(client=client, viewname="statistics:detail")
    assert response.status_code == 200
    # String country IDs are used in the topojson file we download
    # 528 is the ISO ID for the Netherlands
    assert '{"id": "528", "participants": 3}' in response.rendered_content

    stats = cache.get(settings.STATISTICS_SITE_CACHE_KEY)
    assert [*stats["countries"]] == [("NL", 3)]
