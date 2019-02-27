import pytest

from tests.factories import UserFactory
from tests.patients_tests.factories import PatientFactory
from tests.utils import get_view_for_user

from grandchallenge.subdomains.utils import reverse
from grandchallenge.patients.forms import PatientCreateForm, PatientUpdateForm

"""" Tests the forms available for Patient CRUD """


@pytest.mark.django_db
def test_patient_display(client):
    patient = PatientFactory()
    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client, viewname="patients:patient-display", user=staff_user
    )
    assert str(patient.id) in response.rendered_content


@pytest.mark.django_db
def test_patient_create(client):
    staff_user = UserFactory(is_staff=True)
    data = {"name": "test"}

    form = PatientCreateForm(data=data)
    assert form.is_valid()

    form = PatientCreateForm()
    assert not form.is_valid()

    response = get_view_for_user(
        viewname="patients:patient-create",
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

    form = PatientUpdateForm(data=data)
    assert form.is_valid()

    form = PatientUpdateForm()
    assert not form.is_valid()

    response = get_view_for_user(
        client=client,
        method=client.post,
        data=data,
        user=staff_user,
        url=reverse("patients:patient-update", kwargs={"pk": patient.pk}),
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
        url=reverse("patients:patient-delete", kwargs={"pk": patient.pk}),
    )

    assert response.status_code == 302
