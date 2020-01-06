import pytest

from grandchallenge.subdomains.utils import reverse
from tests.factories import PolicyFactory


@pytest.mark.django_db
def test_terms_of_service(client):
    PolicyFactory(body="foo", title="terms")
    response = client.get(reverse("policies:detail", kwargs={"slug": "terms"}))
    assert response.status_code == 200
    assert "foo" in response.rendered_content
