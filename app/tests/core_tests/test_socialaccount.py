import pytest


@pytest.mark.django_db
def test_gmail_login(client):
    response = client.get("/accounts/gmail/login/")
    assert response.status_code == 200

    response = client.post("/accounts/gmail/login/")
    assert response.status_code == 302
    assert response.url.startswith(
        "https://accounts.google.com/o/oauth2/v2/auth"
    )
