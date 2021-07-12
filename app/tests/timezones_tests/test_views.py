import pytest

from grandchallenge.subdomains.utils import reverse


@pytest.mark.django_db
def test_session_timezone(client):
    timezone_orig = client.session.get("timezone")
    assert timezone_orig is None

    response = client.put(
        path=reverse("api:timezone"),
        data={"timezone": "Europe/Amsterdam"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert client.session["timezone"] == "Europe/Amsterdam"

    # Ensure the middleware sets the time zone correctly
    response = client.get(path="/")
    assert response.status_code == 200
    assert response.context[-1]["TIME_ZONE"] == "Europe/Amsterdam"
