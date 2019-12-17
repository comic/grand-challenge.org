import pytest

from grandchallenge.subdomains.utils import reverse
from tests.factories import TermsOfServiceFactory


@pytest.mark.django_db
def test_terms_of_service(client):
    TermsOfServiceFactory(body="foo")
    response = client.get(reverse("terms"))
    assert response.status_code == 200
    assert "foo" in response.rendered_content
