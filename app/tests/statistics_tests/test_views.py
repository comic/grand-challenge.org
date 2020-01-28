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
    assert f"[&quot;NL&quot;, {n_dutch}]" in response.rendered_content
