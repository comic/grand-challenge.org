import pytest

from grandchallenge.subdomains.utils import reverse


@pytest.mark.django_db
def test_session_timezone(client):
    timezone_orig = client.session.get("timezone")
    assert timezone_orig is None

    response = client.post(
        path=reverse("timezones:set"),
        data={"timezone": "Europe/Amsterdam"},
        follow=True,
    )

    assert response.status_code == 200
    assert client.session["timezone"] == "Europe/Amsterdam"

    # Ensure the middleware sets the time zone correctly
    assert response.context[-1]["TIME_ZONE"] == "Europe/Amsterdam"
