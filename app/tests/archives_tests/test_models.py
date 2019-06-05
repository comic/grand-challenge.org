import pytest
from tests.archives_tests.factories import ArchiveFactory


@pytest.mark.django_db
class TestArchivesModels:
    # test functions are added dynamically to this class
    def test_study_str(self):
        model = ArchiveFactory()
        assert str(model) == "<{} {}>".format(
            model.__class__.__name__, model.name
        )


@pytest.mark.django_db
@pytest.mark.parametrize("factory", (ArchiveFactory,))
class TestFactories:
    def test_factory_creation(self, factory):
        try:
            factory()
        except Exception as e:
            pytest.fail(
                f"Failed factory initialization for {str(factory)} with exception: {e}"
            )
