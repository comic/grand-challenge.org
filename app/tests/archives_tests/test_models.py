import pytest
from tests.archives_tests.factories import ArchiveFactory
from tests.model_helpers import batch_test_factories


@pytest.mark.django_db
class TestArchivesModels:
    # test functions are added dynamically to this class
    def test_study_str(self):
        model = ArchiveFactory()
        assert str(model) == "<{} {}>".format(
            model.__class__.__name__, model.name
        )


factories = {
    "archive": ArchiveFactory,
}
batch_test_factories(factories, TestArchivesModels)
