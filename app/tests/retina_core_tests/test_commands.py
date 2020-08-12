import pytest

from grandchallenge.annotations.models import (
    BooleanClassificationAnnotation,
    PolygonAnnotationSet,
)
from grandchallenge.retina_core.management.commands.migratelesionnames import (
    migrate_annotations,
)
from tests.annotations_tests.factories import (
    PolygonAnnotationSetFactory,
    SinglePolygonAnnotationFactory,
)
from tests.factories import ImageFactory, ImagingModalityFactory


@pytest.mark.django_db
class TestMigratelesionnamesCommand:
    def test_testmigratelesionnames_no_match(self):
        annotation = PolygonAnnotationSetFactory(name="No match")
        result = migrate_annotations(PolygonAnnotationSet.objects.all())
        assert result["translated"] == 0
        assert result["no_match"] == [annotation.id]

    def test_testmigratelesionnames_no_match_enface(self):
        annotation = PolygonAnnotationSetFactory(
            name="amd_present::Drusen and drusen like structures::Conical drusen"
        )
        result = migrate_annotations(PolygonAnnotationSet.objects.all())
        assert result["translated"] == 0
        assert result["enface_no_match"] == [annotation.id]

    def test_testmigratelesionnames_no_match_oct(self):
        image = ImageFactory(modality=ImagingModalityFactory(modality="OCT"))
        annotation = PolygonAnnotationSetFactory(
            name="amd_present::Pigment changes & RPE degeneration::Increased pigmentation",
            image=image,
        )
        result = migrate_annotations(PolygonAnnotationSet.objects.all())
        assert result["translated"] == 0
        assert result["oct_no_match"] == [annotation.id]

    def test_testmigratelesionnames_no_match_oct_boolean(self):
        image = ImageFactory(modality=ImagingModalityFactory(modality="OCT"))
        annotation = PolygonAnnotationSetFactory(
            name="other_present::Vascular::Branch retinal artery occlusion",
            image=image,
        )
        result = migrate_annotations(PolygonAnnotationSet.objects.all())
        assert result["translated"] == 0
        assert result["boolean_oct_no_match"] == [annotation.id]

    def test_testmigratelesionnames_correctly_migrated_boolean(self):
        annotation_enface = PolygonAnnotationSetFactory(
            name="other_present::Vascular::Branch retinal artery occlusion"
        )
        assert BooleanClassificationAnnotation.objects.count() == 0
        result = migrate_annotations(PolygonAnnotationSet.objects.all())
        assert result["translated"] == 1
        assert PolygonAnnotationSet.objects.count() == 0
        assert BooleanClassificationAnnotation.objects.count() == 1
        annotation = BooleanClassificationAnnotation.objects.first()
        assert (
            annotation.name
            == "retina::enface::Branch retinal artery occlusion"
        )
        assert annotation.value
        assert annotation.grader == annotation_enface.grader
        assert annotation.image == annotation_enface.image
        assert annotation.created == annotation_enface.created

    def test_testmigratelesionnames_already_migrated(self):
        image = ImageFactory(modality=ImagingModalityFactory(modality="OCT"))
        PolygonAnnotationSetFactory(
            name="retina::oct::macular::Drusen", image=image
        )
        PolygonAnnotationSetFactory(
            name="retina::enface::rf_present::Hard drusen"
        )
        result = migrate_annotations(PolygonAnnotationSet.objects.all())
        assert result["translated"] == 0
        assert result["already_translated"] == 2

    def test_testmigratelesionnames_correctly_migrated(self):
        image = ImageFactory(modality=ImagingModalityFactory(modality="OCT"))
        annotation_oct = PolygonAnnotationSetFactory(
            name="amd_present::Drusen and drusen like structures::Hard Drusen",
            image=image,
        )
        annotation_enface = PolygonAnnotationSetFactory(
            name="drusen and drusen like structures::hard drusen"
        )
        result = migrate_annotations(PolygonAnnotationSet.objects.all())
        assert result["translated"] == 2
        annotation_enface.refresh_from_db()
        assert (
            annotation_enface.name == "retina::enface::rf_present::Hard drusen"
        )
        annotation_oct.refresh_from_db()
        assert annotation_oct.name == "retina::oct::macular::Drusen"

    def test_testmigratelesionnames_correctly_migrated_case_insensitive(self):
        image = ImageFactory(modality=ImagingModalityFactory(modality="OCT"))
        annotation_oct = PolygonAnnotationSetFactory(
            name="amd_present::DrUsEn AnD DrUsEn lIkE sTruCtUrEs::HARD dRuSeN",
            image=image,
        )
        annotation_enface = PolygonAnnotationSetFactory(
            name="DrUsEn AnD DrUsEn lIkE sTruCtUrEs::HARD dRuSeN"
        )
        result = migrate_annotations(PolygonAnnotationSet.objects.all())
        assert result["translated"] == 2
        annotation_enface.refresh_from_db()
        assert (
            annotation_enface.name == "retina::enface::rf_present::Hard drusen"
        )
        annotation_oct.refresh_from_db()
        assert annotation_oct.name == "retina::oct::macular::Drusen"

    def test_testmigratelesionnames_combined(self):
        image = ImageFactory(modality=ImagingModalityFactory(modality="OCT"))
        annotation_oct = PolygonAnnotationSetFactory(
            name="amd_present::Drusen and drusen like structures::Hard Drusen",
            image=image,
        )
        annotation_enface = PolygonAnnotationSetFactory(
            name="drusen and drusen like structures::hard drusen"
        )
        PolygonAnnotationSetFactory(
            name="retina::oct::macular::Drusen", image=image
        )
        PolygonAnnotationSetFactory(
            name="retina::enface::rf_present::Hard drusen"
        )
        PolygonAnnotationSetFactory(
            name="other_present::Vascular::Branch retinal artery occlusion",
        )
        annotation_oct_no_match_boolean = PolygonAnnotationSetFactory(
            name="other_present::Vascular::Branch retinal artery occlusion",
            image=image,
        )
        annotation_oct_no_match = PolygonAnnotationSetFactory(
            name="amd_present::Pigment changes & RPE degeneration::Increased pigmentation",
            image=image,
        )
        annotation_enface_no_match = PolygonAnnotationSetFactory(
            name="amd_present::Drusen and drusen like structures::Conical drusen"
        )
        annotation_no_match = PolygonAnnotationSetFactory(name="No match")

        assert BooleanClassificationAnnotation.objects.count() == 0
        result = migrate_annotations(PolygonAnnotationSet.objects.all())
        assert result["translated"] == 3
        assert BooleanClassificationAnnotation.objects.count() == 1
        assert result["already_translated"] == 2
        assert result["boolean_oct_no_match"] == [
            annotation_oct_no_match_boolean.id
        ]
        assert result["oct_no_match"] == [annotation_oct_no_match.id]
        assert result["enface_no_match"] == [annotation_enface_no_match.id]
        assert result["no_match"] == [annotation_no_match.id]
        annotation_enface.refresh_from_db()
        assert (
            annotation_enface.name == "retina::enface::rf_present::Hard drusen"
        )
        annotation_oct.refresh_from_db()
        assert annotation_oct.name == "retina::oct::macular::Drusen"

    def test_testmigratelesionnames_unique_violation_appends(self):
        annotation = PolygonAnnotationSetFactory(
            name="drusen and drusen like structures::hard drusen"
        )
        SinglePolygonAnnotationFactory(annotation_set=annotation),
        SinglePolygonAnnotationFactory(annotation_set=annotation),
        annotation_dup = PolygonAnnotationSetFactory(
            name="retina::enface::rf_present::Hard drusen",
            grader=annotation.grader,
            image=annotation.image,
            created=annotation.created,
        )
        SinglePolygonAnnotationFactory(annotation_set=annotation_dup),
        SinglePolygonAnnotationFactory(annotation_set=annotation_dup),
        assert annotation_dup.singlepolygonannotation_set.count() == 2
        result = migrate_annotations(PolygonAnnotationSet.objects.all())
        assert result["translated"] == 1
        assert result["already_translated"] == 1
        assert PolygonAnnotationSet.objects.count() == 1
        annotation_dup.refresh_from_db()
        assert annotation_dup.singlepolygonannotation_set.count() == 4
