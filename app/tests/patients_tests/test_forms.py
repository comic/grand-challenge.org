import pytest
from tests.factories import UserFactory
from tests.patients_tests.factories import PatientFactory
from tests.utils import get_view_for_user

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
    form = PatientCreateForm(data={"name": "test"})
    assert form.is_valid()

    form = PatientCreateForm()
    assert not form.is_valid()


@pytest.mark.django_db
def test_patient_update(client):
    form = PatientUpdateForm(data={"name": "test"})
    assert form.is_valid()

    form = PatientUpdateForm()
    assert not form.is_valid()


@pytest.mark.django_db
def test_patient_delete(client):
    patient = PatientFactory()
    staff_user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client,
        viewname="patients:patient-delete",
        user=staff_user,
        args=patient.id,
    )

    assert response.status_code == 302
    assert patient is None
