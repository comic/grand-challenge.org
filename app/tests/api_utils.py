import json

from django.utils.encoding import force_text
from rest_framework.authtoken.models import Token
from rest_framework.renderers import JSONRenderer
from grandchallenge.subdomains.utils import reverse

from tests.factories import UserFactory


def assert_api_crud(
    client, table_reverse, expected_table, factory, serializer
):
    _, token = get_staff_user_with_token()
    table_url = reverse(table_reverse)

    record = factory()
    record_id = str(record.pk)
    json_record = get_record_as_json(factory, serializer)

    # Rests record display
    assert_record_display(client, table_url, token, record_id)

    # Tests record update
    assert_record_update(client, table_url, token, json_record, record_id)

    # Tests record remove
    assert_record_remove(client, table_url, token, record_id)

    # Tests table display
    assert_table_display(client, table_url, token, expected_table)

    # Tests table create
    assert_table_create(client, table_url, token, json_record)


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
def get_record_as_json(factory, serializer):
    new_record = factory()
    serialized = serializer(new_record)
    json_record = JSONRenderer().render(serialized.data)
    data = json.loads(json_record)

    try:
        del data["id"]
    except KeyError:
        pass

    new_record.delete()
    return json.dumps(data)


# Acquires a staff account alongside a corresponding user token
def get_staff_user_with_token():
    user = UserFactory(is_staff=True)
    token = Token.objects.create(user=user)

    return user, token.key
