import pytest

from tests.patients_tests.factories import PatientFactory


@pytest.mark.django_db
def test_study_str():
    model = PatientFactory()
    assert str(model) == f"<{model.__class__.__name__} {model.name}>"
