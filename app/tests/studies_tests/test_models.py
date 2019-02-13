import pytest
from tests.studies_tests.factories import StudyFactory
from tests.model_helpers import batch_test_factories


@pytest.mark.django_db
class TestStudiesModels:
    # test functions are added dynamically to this class
    def test_study_str(self):
        model = StudyFactory()
        assert str(model) == "<{} {}>".format(
            model.__class__.__name__, model.name
        )


factories = {"study": StudyFactory}
batch_test_factories(factories, TestStudiesModels)
