import pytest

from grandchallenge.retina_core.management.commands.migratepatientsandstudies import (
    iterate_objects,
    migrate_fields,
    perform_migration,
    validate_field_lengths,
)
from tests.cases_tests.factories import ImageFactoryWithoutImageFile
from tests.factories import UserFactory
from tests.patients_tests.factories import PatientFactory
from tests.studies_tests.factories import StudyFactory


@pytest.mark.django_db
class TestMigratePatientsAndStudiesCommand:
    def test_iterator(self):
        test_result = []

        def test_method(o):
            test_result.append(o)

        users = UserFactory.create_batch(20)
        iterate_objects(users, test_method, page_size=5)
        assert len(test_result) == 20

    def test_migrate_fields(self):
        image = ImageFactoryWithoutImageFile(
            patient_id="", study_description="", study_date=None
        )
        migrate_fields(image)
        image.refresh_from_db()
        assert image.patient_id == image.study.patient.name
        assert image.study_description == image.study.name
        if image.study.datetime is not None:
            assert image.study_date == image.study.datetime.date()

    def test_validate_field_lengths(self):
        validate_field_lengths()
        _ = PatientFactory.create_batch(10)
        validate_field_lengths()
        _ = StudyFactory.create_batch(10)
        validate_field_lengths()
        p = PatientFactory(name="a" * 65)
        with pytest.raises(ValueError):
            validate_field_lengths()
        p.delete()
        validate_field_lengths()
        s = StudyFactory(name="a" * 65)
        with pytest.raises(ValueError):
            validate_field_lengths()
        s.delete()
        validate_field_lengths()

    def test_perform_migration(self):
        assert perform_migration() == 0
        _ = ImageFactoryWithoutImageFile(study=None)
        assert perform_migration() == 0
        invalid_image = ImageFactoryWithoutImageFile(
            study=StudyFactory(name="a" * 65)
        )
        with pytest.raises(ValueError):
            perform_migration()
        _ = ImageFactoryWithoutImageFile()
        with pytest.raises(ValueError):
            perform_migration()
        invalid_image.study.delete()
        assert perform_migration() == 1
        _ = ImageFactoryWithoutImageFile.create_batch(10)
        assert perform_migration() == 11
        assert perform_migration() == 11
