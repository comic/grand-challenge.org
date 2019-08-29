import pytest
from django.core.exceptions import ObjectDoesNotExist

from tests.archives_tests.factories import ArchiveFactory
from tests.cases_tests.factories import ImageFactoryWithImageFile
from tests.model_helpers import do_test_factory


@pytest.mark.django_db
class TestArchivesModels:
    # test functions are added dynamically to this class
    def test_str(self):
        model = ArchiveFactory()
        assert str(model) == "<{} {}>".format(
            model.__class__.__name__, model.name
        )


@pytest.mark.django_db
@pytest.mark.parametrize("factory", (ArchiveFactory,))
class TestFactories:
    def test_factory_creation(self, factory):
        do_test_factory(factory)


@pytest.mark.django_db
class TestCascadeDelete:
    def test_removes_all_related_models(
        self, ArchivePatientStudyImageSet, AnnotationSetForImage
    ):
        apsi_set = ArchivePatientStudyImageSet
        annotation_set = AnnotationSetForImage(
            retina_grader=True, image=apsi_set.images111[0]
        )
        image_not_in_archive = ImageFactoryWithImageFile(
            study=apsi_set.study111
        )
        apsi_set.archive1.delete()
        all_deleted_models = (
            apsi_set.archive1,
            apsi_set.patient11,
            apsi_set.patient12,
            apsi_set.study111,
            apsi_set.study112,
            apsi_set.study113,
            apsi_set.study121,
            apsi_set.study122,
            *apsi_set.images111,
            *apsi_set.images112,
            *apsi_set.images113,
            *apsi_set.images122,
            *apsi_set.images121,
            annotation_set.measurement,
            annotation_set.boolean,
            annotation_set.polygon,
            annotation_set.coordinatelist,
            annotation_set.singlelandmarks[0],
            annotation_set.etdrs,
            annotation_set.integer,
            image_not_in_archive,
        )
        for model in all_deleted_models:
            with pytest.raises(ObjectDoesNotExist):
                assert model.refresh_from_db()

        not_deleted_models = (
            apsi_set.archive2,
            *apsi_set.images211,
            annotation_set.landmark,
            *annotation_set.singlelandmarks[1:],
        )
        for model in not_deleted_models:
            assert model.refresh_from_db() is None
