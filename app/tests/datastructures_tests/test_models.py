import pytest
from tests.retina_images_tests.factories import RetinaImageFactory
from tests.studies_tests.factories import StudyFactory
from tests.patients_tests.factories import PatientFactory
from tests.archives_tests.factories import ArchiveFactory
from tests.model_helpers import batch_test_factories


@pytest.mark.django_db
class TestDatastructuresModels:
    # test functions are added dynamically to this class
    def test_default_datastructure_str(self):
        archive = ArchiveFactory()
        assert str(archive) == "<{} {}>".format(
            archive.__class__.__name__, archive.name
        )


factories = {
    "archive": ArchiveFactory,
    "patient": PatientFactory,
}
batch_test_factories(factories, TestDatastructuresModels)


