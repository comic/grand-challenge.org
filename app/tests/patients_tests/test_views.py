import pytest

from tests.factories import PatientFactory, UserFactory
from tests.utils import get_view_for_user

"""" Tests the forms available for Patient CRUD """


@pytest.mark.django_db
def test_patient_list(client):
    inserted = PatientFactory()

    staff_user = UserFactory(is_staff=True)
    response = get_view_for_user(
        client=client, viewname="patients:patient-display", user=staff_user
    )
    assert str(inserted.id) in response.rendered_content
