import json

import pytest
from django.forms.models import model_to_dict
from django.urls import reverse
from django.utils.encoding import force_text
from rest_framework.authtoken.models import Token

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
    record_fields = model_to_dict(record, fields=[field.name for field in record._meta.fields])
    assert_record_deletion(client, record_url, token, record.id)

    # Attempts to create a new record through the API
    new_record_id = assert_table_insert(client, table_url, token, json.loads(record_fields))

    # Attempts to display the object
    assert_record_display(client, record_url, token, new_record_id)

    # Acquires another object, and attempts to update the current record with the new information
    record = object_factory()
    record_fields = model_to_dict(record, fields=[field.name for field in record._meta.fields])
    assert_record_update(client, record_url, json.loads(record_fields), record.id)


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
        url + str(record_id) + "/",
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token)
    json_response = json.loads(response.content)

    assert response.status_code == 200
    assert json_response["id"] == id


def assert_record_update(client, url, token, json_record, record_id, fields):
    response = client.post(
        url + str(record_id) + "/",
        json_record,
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token)
    json_response = json.loads(response.content)
    del json_response["id"]

    assert response.status_code == 200
    assert sorted(json_record.items()) == sorted(json_response.items())


def assert_record_deletion(client, url, token, record_id):
    response = client.delete(
        url + str(record_id) + "/",
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token)

    assert response.status_code == 204


def dict_to_cleaned_json(fields):
    del fields["id"]
    return json.loads(fields)
