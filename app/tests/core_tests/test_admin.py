import pytest

from grandchallenge.subdomains.utils import reverse


@pytest.mark.django_db
def test_admin_login_is_site_login(client):
    # Site login is required for 2FA and social auth flow
    login_url = reverse("admin:login")

    response = client.get(path=login_url)

    assert login_url == "https://testserver/django-admin/login/"
    assert response.status_code == 302
    assert response.url == "/accounts/login/"
