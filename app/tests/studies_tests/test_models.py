import pytest
from tests.studies_tests.factories import StudyFactory


@pytest.mark.django_db
class TestStudiesModels:
    # test functions are added dynamically to this class
    def test_study_str(self):
        model = StudyFactory()
        assert str(model) == "{} <{} {}>".format(
            model.patient, model.__class__.__name__, model.name
        )


@pytest.mark.django_db
@pytest.mark.parametrize("factory", (StudyFactory,))
class TestFactories:
    def test_factory_creation(self, factory):
        try:
            factory()
        except Exception as e:
            pytest.fail(
                f"Failed factory initialization for {str(factory)} with exception: {e}"
            )
