import json

import pytest
from django.urls import reverse
from django.utils.encoding import force_text
from rest_framework.authtoken.models import Token

from grandchallenge.patients.serializer import PatientSerializer
from tests.factories import UserFactory, PatientFactory


def get_staff_user_with_token():
    user = UserFactory(is_staff=True)
    token = Token.objects.create(user=user)

    return user, token.key


@pytest.mark.django_db
@pytest.mark.parametrize(
    "test_input, expected",
    [("patients", "Patient Table")],  # ("patient", "Patient Record")
)
def test_api_pages(client, test_input, expected):
    _, token = get_staff_user_with_token()
    url = reverse(f"patients:{test_input}")
    patient = PatientFactory()

    # Checks the HTML View
    test_table_access(client, url, token, expected)
    # Checks insertions and acquires id
    record_id = test_table_insert(client, url, token, patient)
    test_record_display(client, url, token, record_id)
    test_record_update(client, url, token, patient, id)
    test_record_delete(client, url, token, id)


def test_table_access(client, url, token, expected):
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


def test_table_insert(client, url, token, patient):
    response = client.post(
        url,
        PatientSerializer.serialize("json", patient),
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token)
    json_response = json.loads(response.content)

    assert response.status_code == 200
    return json_response["id"]


def test_record_display(client, url, token, id):
    response = client.get(url + "/" + str(id), HTTP_ACCEPT="application/json", HTTP_AUTHORIZATION="Token " + token)
    json_response = json.loads(response.content)

    assert response.status_code == 200
    assert json_response["id"] == id


def test_record_update(client, url, token, patient, id):
    patient.height = patient.height + 10

    response = client.post(
        url + "/" + id,
        PatientSerializer.serialize("json", patient),
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token)
    json_response = json.loads(response.content)

    assert response.status_code == 200
    assert json_response["height"] == patient.height


def test_record_delete(client, url, token, id):
    response = client.delete(url + "/" + id, HTTP_ACCEPT="application/json", HTTP_AUTHORIZATION="Token " + token)

    assert response.status_code == 200
