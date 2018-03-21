import pytest

from core.urlresolvers import reverse


@pytest.mark.django_db
def test_main(client):
    url = reverse('home')
    response = client.get(url)
    assert response.status_code == 200
