import json

from django.conf import settings
from django.forms.models import model_to_dict
from django.utils.encoding import force_text
from rest_framework.authtoken.models import Token
from grandchallenge.subdomains.utils import reverse

from tests.factories import UserFactory


def assert_api_crud(
    client, table_reverse, expected_table, factory, invalid_fields
):
    invalid_fields.append("id")

    _, token = get_staff_user_with_token()
    table_url = reverse(table_reverse)

    record = factory()
    record_id = str(record.pk)
    record_dict = get_record_as_dict(factory, invalid_fields)

    # Rests record display
    assert_record_display(client, table_url, token, record_id)

    # Tests record update
    assert_record_update(client, table_url, token, record_dict, record_id)

    # Tests record remove
    assert_record_remove(client, table_url, token, record_id)

    # Tests table display
    assert_table_display(client, table_url, token, expected_table)

    # Tests table create
    assert_table_create(client, table_url, token, record_dict)


def assert_table_display(client, url, token, expected):
    response = client.get(
        url, HTTP_ACCEPT="text/html", HTTP_AUTHORIZATION="Token " + token
    )
    assert expected in force_text(response.content)
    assert response.status_code == 200

    # There should be no content, but we should be able to do json.loads
    response = client.get(
        url,
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token,
    )
    assert response.status_code == 200
    assert not json.loads(response.content)


def assert_table_create(client, url, token, json_record):
    response = client.post(
        url,
        json_record,
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token,
    )

    assert response.status_code == 201


def assert_record_display(client, url, token, record_id):
    response = client.get(
        url + record_id + "/",
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token,
    )
    json_response = json.loads(response.content)

    assert response.status_code == 200
    assert json_response["id"] == record_id


def assert_record_update(client, url, token, json_record, record_id):
    response = client.put(
        url + record_id + "/",
        json_record,
        content_type="application/json",
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token,
    )

    assert response.status_code == 200


def assert_record_remove(client, url, token, record_id):
    response = client.delete(
        url + record_id + "/",
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token,
    )

    assert response.status_code == 204


# Creates a new record and converts it to JSON, removing the original entry afterwards
def get_record_as_dict(factory, invalid_fields) -> dict:
    new_record = factory()
    record_dict = model_to_dict(new_record)

    for field in invalid_fields:
        if field in record_dict:
            del record_dict[field]

    new_record.delete()
    return record_dict


# Acquires a staff account alongside a corresponding user token
def get_staff_user_with_token() -> [settings.AUTH_USER_MODEL, str]:
    user = UserFactory(is_staff=True)
    token = Token.objects.create(user=user)

    return user, token.key
