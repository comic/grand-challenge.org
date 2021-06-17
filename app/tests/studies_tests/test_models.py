import pytest

from tests.studies_tests.factories import StudyFactory


@pytest.mark.django_db
def test_study_str():
    model = StudyFactory()
    assert str(model) == "{} <{} {}>".format(
        model.patient, model.__class__.__name__, model.name
    )
