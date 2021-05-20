import pytest

from tests.patients_tests.factories import PatientFactory


@pytest.mark.django_db
class TestPatientsModels:
    # test functions are added dynamically to this class
    def test_study_str(self):
        model = PatientFactory()
        assert str(model) == "<{} {}>".format(
            model.__class__.__name__, model.name
        )
