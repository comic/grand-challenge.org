import json

from django.forms.models import model_to_dict
from django.utils.encoding import force_text
from rest_framework.authtoken.models import Token
from grandchallenge.subdomains.utils import reverse

from tests.factories import UserFactory


def assert_api_crud(client, table_reverse, expected_table, object_factory):
    _, token = get_staff_user_with_token()
    table_url = reverse(table_reverse)

    # Checks the HTML View
    assert_table_access(client, table_url, token, expected_table)

    # Creates an object and then serializes it into JSON before deleting it from the DB
    record = object_factory()
    record_fields = model_to_dict(
        record, fields=[field.name for field in record._meta.fields]
    )
    assert_record_deletion(client, table_url, token, record.pk)

    # Attempts to create a new record through the API
    new_record_id = assert_table_insert(
        client, table_url, token, dict_to_json(record_fields)
    )

    # Attempts to display the object
    assert_record_display(client, table_url, token, new_record_id)

    # Acquires another object, and attempts to update the current record with the new information
    record = object_factory()
    record_fields = model_to_dict(
        record, fields=[field.name for field in record._meta.fields]
    )
    assert_record_update(
        client, table_url, token, dict_to_json(record_fields), record.pk
    )


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
        HTTP_AUTHORIZATION="Token " + token,
    )
    json_response = json.loads(response.content)

    assert response.status_code == 201
    return json_response["id"]


def assert_record_display(client, url, token, record_id):
    response = client.get(
        url + str(record_id) + "/",
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token,
    )
    json_response = json.loads(response.content)

    assert response.status_code == 200
    assert json_response["id"] == record_id


def assert_record_update(client, url, token, json_record, record_id):
    response = client.put(
        url + str(record_id) + "/",
        json_record,
        content_type="application/json",
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token,
    )

    assert response.status_code == 200


def assert_record_deletion(client, url, token, record_id):
    response = client.delete(
        url + str(record_id) + "/",
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token,
    )

    assert response.status_code == 204


def dict_to_json(dict_object):
    dict_string = "{ "
    for key, val in dict_object.items():
        dict_string += '"%s": "%s", ' % (key, val)

    dict_string = dict_string[:-2]
    dict_string += " }"
    return json.loads(dict_string)


def get_staff_user_with_token():
    user = UserFactory(is_staff=True)
    token = Token.objects.create(user=user)

    return user, token.key
