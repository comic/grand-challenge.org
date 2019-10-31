import json

from django.conf import settings
from django.forms.models import model_to_dict
from django.utils.encoding import force_text
from guardian.shortcuts import assign_perm
from rest_framework.authtoken.models import Token

from grandchallenge.subdomains.utils import reverse
from tests.factories import UserFactory


def assert_api_read_only(
    client, table_reverse, expected_table, user_field, factory
):
    user, token = get_staff_user_with_token()
    table_url = reverse(table_reverse)

    factory_kwargs = {}
    if user_field:
        factory_kwargs[user_field] = user

    # Tests table display
    assert_table_list(client, table_url, token, expected_table)

    record = factory(**factory_kwargs)
    record_id = str(record.pk)

    # Assigns permissions to token user
    model_name = factory._meta.model._meta.model_name
    for permission_type in factory._meta.model._meta.default_permissions:
        permission_name = f"{permission_type}_{model_name}"
        assign_perm(permission_name, user, record)

    # Rests record display
    assert_record_display(client, table_url, token, record_id)


def assert_api_crud(
    client, table_reverse, expected_table, factory, user_field, invalid_fields
):
    # Ensures there are no entries present of the current model
    assert factory._meta.model.objects.all().count() == 0

    invalid_fields.append("id")

    user, token = get_staff_user_with_token()
    table_url = reverse(table_reverse)

    factory_kwargs = {}
    if user_field:
        factory_kwargs[user_field] = user

    # Creates record model object and serialized record information
    record = factory(**factory_kwargs)
    record_id = str(record.pk)
    record_dict = get_record_as_dict(factory, factory_kwargs, invalid_fields)

    # Assigns permissions to token user
    model_name = factory._meta.model._meta.model_name
    for permission_type in factory._meta.model._meta.default_permissions:
        permission_name = f"{permission_type}_{model_name}"
        assign_perm(permission_name, user, record)

    # Rests record display
    assert_record_display(client, table_url, token, record_id)

    # Tests record update
    assert_record_update(client, table_url, token, record_dict, record_id)

    # Tests record remove
    assert_record_remove(client, table_url, token, record_id)

    # Tests table display
    assert_table_list(client, table_url, token, expected_table)

    # Ensures no records are left while testing the creation view
    factory._meta.model.objects.all().delete()

    # Tests table create
    assert_table_create(client, table_url, token, record_dict)


def assert_table_list(client, url, token, expected):
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
    assert json.loads(response.content)


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
def get_record_as_dict(factory, factory_kwargs, invalid_fields) -> dict:
    new_record = factory(**factory_kwargs)
    record_dict = model_to_dict(new_record)

    count = factory._meta.model.objects.all().count()

    for field in invalid_fields:
        if field in record_dict:
            del record_dict[field]

    new_record.delete()
    assert factory._meta.model.objects.all().count() == count - 1
    return record_dict


# Acquires a staff account alongside a corresponding user token
def get_staff_user_with_token() -> [settings.AUTH_USER_MODEL, str]:
    user = UserFactory(is_staff=True)
    token = Token.objects.create(user=user)

    return user, token.key
