from datetime import timedelta

import pytest
from dateutil.parser import isoparse
from django.utils.timezone import now


@pytest.mark.django_db
def test_security_txt_expiry_valid(client):
    # If this test fails be sure to review the security.txt
    # and update the expiry date
    response = client.get("/.well-known/security.txt")

    assert response.status_code == 200

    lines = response.rendered_content.splitlines()

    # Last line should contain the expiry clause
    key, value = lines[-1].split(":", 1)

    assert key == "Expires"

    expiry_date = isoparse(value.strip())
    expires_in = expiry_date - now()

    # Must be more than a month and less than a year
    # See https://www.rfc-editor.org/rfc/rfc9116#name-expires
    assert timedelta(days=28) < expires_in < timedelta(days=365)
