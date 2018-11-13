import pytest

from tests.factories import PatientFactory
from tests.utils import validate_logged_in_view


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        "patients:patient-list",
        "patients:patient-create",
        "patients:patient-update",
        "patients:patient-delete",
    ],
)
def test_patient_form_views(client, view):
    if view in ["patients:patient-update", "patients:patient-delete"]:
        reverse_kwargs = {"short_name": PatientFactory().short_name}
    else:
        reverse_kwargs = {}

    validate_logged_in_view(
        client=client, viewname=view, reverse_kwargs=reverse_kwargs
    )
