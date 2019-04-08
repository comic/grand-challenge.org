import pytest

from grandchallenge.patients.forms import PatientForm
from grandchallenge.subdomains.utils import reverse
from tests.factories import UserFactory
from tests.patients_tests.factories import PatientFactory
from tests.utils import get_view_for_user

"""" Tests the forms available for Patient CRUD """


@pytest.mark.django_db
def test_patient_display(client):
    patient = PatientFactory()
    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client, viewname="patients:list", user=staff_user
    )
    assert str(patient.id) in response.rendered_content


@pytest.mark.django_db
def test_patient_create(client):
    staff_user = UserFactory(is_staff=True)
    data = {"name": "test"}

    form = PatientForm(data=data)
    assert form.is_valid()

    form = PatientForm()
    assert not form.is_valid()

    response = get_view_for_user(
        viewname="patients:create",
        client=client,
        method=client.post,
        data=data,
        user=staff_user,
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_patient_update(client):
    staff_user = UserFactory(is_staff=True)
    patient = PatientFactory()
    data = {"name": "test"}

    form = PatientForm(data=data)
    assert form.is_valid()

    form = PatientForm()
    assert not form.is_valid()

    response = get_view_for_user(
        client=client,
        method=client.post,
        data=data,
        user=staff_user,
        url=reverse("patients:update", kwargs={"pk": patient.pk}),
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_patient_delete(client):
    patient = PatientFactory()
    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client,
        method=client.post,
        user=staff_user,
        url=reverse("patients:delete", kwargs={"pk": patient.pk}),
    )

    assert response.status_code == 302
