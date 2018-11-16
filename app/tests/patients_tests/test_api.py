import json

import pytest
from django.urls import reverse
from django.utils.encoding import force_text
from rest_framework.authtoken.models import Token

from django.core import serializers
from tests.factories import UserFactory, PatientFactory


def get_staff_user_with_token():
    user = UserFactory(is_staff=True)
    token = Token.objects.create(user=user)

    return user, token.key


@pytest.mark.django_db
@pytest.mark.parametrize(
    "table_reverse, record_reverse, expected_table, object_factory",
    [("patients:patients", "patients:patients", "Patient Table", PatientFactory)],
)
def test_api_pages(client, table_reverse, record_reverse, expected_table, object_factory):
    assert_api_crud(client, table_reverse, record_reverse, expected_table, object_factory)


def assert_api_crud(client, table_reverse, record_reverse, expected_table, object_factory):
    _, token = get_staff_user_with_token()
    table_url = reverse(table_reverse)
    record_url = reverse(record_reverse)

    # Checks the HTML View
    assert_table_access(client, table_url, token, expected_table)

    # Creates an object and then serializes it into JSON before deleting it from the DB
    record = object_factory()
    json_record = remove_id_from_json(json.loads(serializers.serialize("json", [record, ])[1:-1]))
    assert_record_deletion(client, record_url, token, record.id)

    # Removes the ID tag from the JSON object and then reinserts the object into the DB
    for element in json_record:
        element.pop("id", None)

    new_record_id = assert_table_insert(client, table_url, token, json_record)

    # Attempts to display the object
    assert_record_display(client, record_url, token, new_record_id)

    # Acquires another object, and attempts to update the current record with the new information
    # TODO: Move JSON extraction and scrubbing into a method
    record = object_factory()
    json_record = remove_id_from_json(json.loads(serializers.serialize("json", [record, ])[1:-1]))

    assert_record_deletion(client, record_url, token, record.id)
    assert_record_update(client, record_url, json_record, record.id)


def assert_table_access(client, url, token, expected):
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


def assert_table_insert(client, url, token, json_record):
    response = client.post(
        url,
        json_record,
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token)
    json_response = json.loads(response.content)

    assert response.status_code == 200
    return json_response["id"]


def assert_record_display(client, url, token, record_id):
    response = client.get(
        url + str(record_id),
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token)
    json_response = json.loads(response.content)

    assert response.status_code == 200
    assert json_response["id"] == id


def assert_record_update(client, url, token, json_record, record_id):
    response = client.post(
        url + str(record_id),
        json_record,
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token)
    json_response = remove_id_from_json(json.loads(response.content))

    assert response.status_code == 200
    assert sorted(json_record.items()) == sorted(json_response.items())


def assert_record_deletion(client, url, token, record_id):
    response = client.delete(
        url + str(record_id),
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token)

    assert response.status_code == 200


def remove_id_from_json(json_object):
    for element in json_object:
        if "id" in element:
            del element["id"]

    return json_object
