import pytest

from tests.factories import PatientFactory
from tests.utils import get_view_for_user

"""" Tests the forms available for Patient CRUD """


@pytest.mark.django_db
def test_patient_list(client):
    visible = PatientFactory()
    response = get_view_for_user(client=client, viewname="patients:patient-list")
    assert str(visible.id) in response.rendered_content

