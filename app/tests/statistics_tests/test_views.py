import pytest

from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_get_statistics(client):
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
