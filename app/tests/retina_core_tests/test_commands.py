import pytest

from grandchallenge.annotations.models import (
    BooleanClassificationAnnotation,
    ImageTextAnnotation,
    OctRetinaImagePathologyAnnotation,
    PolygonAnnotationSet,
    RetinaImagePathologyAnnotation,
)
from grandchallenge.retina_core.management.commands.migratelesionnames import (
    migrate_annotations,
)
from grandchallenge.retina_core.management.commands.migrateunmatchedlesionnames import (
    migrate_oct_annotations,
)
from grandchallenge.retina_core.management.commands.setretinapathologies import (
    pathology_options_enface,
    pathology_options_oct,
    set_retina_pathologies,
)
from tests.annotations_tests.factories import (
    ImageTextAnnotationFactory,
    PolygonAnnotationSetFactory,
    RetinaImagePathologyAnnotationFactory,
    SinglePolygonAnnotationFactory,
)
from tests.factories import ImageFactory, ImagingModalityFactory, UserFactory


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


@pytest.mark.django_db
class TestSetRetinaPathologiesCommand:
    def test_testsetretinapathologies_old(self):
        PolygonAnnotationSetFactory(name="No match")
        PolygonAnnotationSetFactory(name="retina::too_small")
        result = set_retina_pathologies(PolygonAnnotationSet.objects.all())
        assert result["pathology_set"] == 0
        assert result["old_annotation"] == 2
        assert len(result["non_matching_pathology"]) == 0

    def test_testsetretinapathologies_no_match(self):
        annotation = PolygonAnnotationSetFactory(
            name="retina::enface::non_matching_pathology::bla"
        )
        result = set_retina_pathologies(PolygonAnnotationSet.objects.all())
        assert result["pathology_set"] == 0
        assert result["old_annotation"] == 0
        assert len(result["non_matching_pathology"]) == 1
        assert result["non_matching_pathology"] == [
            {"id": annotation.id, "name": annotation.name}
        ]

    def test_testsetretinapathologies_created(self):
        annotation = PolygonAnnotationSetFactory(
            name=f"retina::enface::{pathology_options_enface[0]}::bla"
        )
        assert RetinaImagePathologyAnnotation.objects.all().count() == 0
        result = set_retina_pathologies(PolygonAnnotationSet.objects.all())
        assert result["pathology_set"] == 1
        assert result["old_annotation"] == 0
        assert len(result["non_matching_pathology"]) == 0
        assert RetinaImagePathologyAnnotation.objects.all().count() == 1
        pathology_annotation = RetinaImagePathologyAnnotation.objects.first()
        assert pathology_annotation.image == annotation.image
        assert pathology_annotation.grader == annotation.grader
        for v in pathology_options_enface:
            assert getattr(pathology_annotation, v) == (
                v == pathology_options_enface[0]
            )

    def test_testsetretinapathologies_updated(self):
        annotation = PolygonAnnotationSetFactory(
            name=f"retina::enface::{pathology_options_enface[0]}::bla"
        )
        pathology_annotation = RetinaImagePathologyAnnotationFactory(
            **{
                "image": annotation.image,
                "grader": annotation.grader,
                pathology_options_enface[0]: False,
            }
        )
        assert RetinaImagePathologyAnnotation.objects.all().count() == 1
        result = set_retina_pathologies(PolygonAnnotationSet.objects.all())
        assert result["pathology_set"] == 1
        assert result["old_annotation"] == 0
        assert len(result["non_matching_pathology"]) == 0
        assert RetinaImagePathologyAnnotation.objects.all().count() == 1
        pathology_annotation.refresh_from_db()
        assert pathology_annotation.image == annotation.image
        assert pathology_annotation.grader == annotation.grader
        assert (
            getattr(pathology_annotation, pathology_options_enface[0]) is True
        )

    def test_testsetretinapathologies_oct_legacy_removed(self):
        annotation = PolygonAnnotationSetFactory(
            name=f"retina::oct::{pathology_options_oct[0]}::bla"
        )
        RetinaImagePathologyAnnotationFactory(
            **{"image": annotation.image, "grader": annotation.grader}
        )
        assert RetinaImagePathologyAnnotation.objects.all().count() == 1
        assert OctRetinaImagePathologyAnnotation.objects.all().count() == 0
        result = set_retina_pathologies(PolygonAnnotationSet.objects.all())
        assert result["pathology_set"] == 1
        assert result["old_annotation"] == 0
        assert len(result["non_matching_pathology"]) == 0
        assert RetinaImagePathologyAnnotation.objects.all().count() == 0
        assert OctRetinaImagePathologyAnnotation.objects.all().count() == 1
        oct_pathology_annotation = (
            OctRetinaImagePathologyAnnotation.objects.first()
        )
        assert oct_pathology_annotation.image == annotation.image
        assert oct_pathology_annotation.grader == annotation.grader
        assert (
            getattr(oct_pathology_annotation, pathology_options_oct[0]) is True
        )

    def test_testsetretinapathologies_oct(self):
        annotation = PolygonAnnotationSetFactory(
            name=f"retina::oct::{pathology_options_oct[0]}::bla"
        )
        assert OctRetinaImagePathologyAnnotation.objects.all().count() == 0
        result = set_retina_pathologies(PolygonAnnotationSet.objects.all())
        assert result["pathology_set"] == 1
        assert result["old_annotation"] == 0
        assert len(result["non_matching_pathology"]) == 0
        assert RetinaImagePathologyAnnotation.objects.all().count() == 0
        assert OctRetinaImagePathologyAnnotation.objects.all().count() == 1
        oct_pathology_annotation = (
            OctRetinaImagePathologyAnnotation.objects.first()
        )
        assert oct_pathology_annotation.image == annotation.image
        assert oct_pathology_annotation.grader == annotation.grader
        assert (
            getattr(oct_pathology_annotation, pathology_options_oct[0]) is True
        )


@pytest.mark.django_db
class TestOCTMigratelesionnamesCommand:
    def test_migrateunmatchedocts_none(self):
        result = migrate_oct_annotations(PolygonAnnotationSet.objects.all())
        assert len(result["translated_annotations"]) == 0
        assert result["non_oct"] == []

    def test_migrateunmatchedocts_non_oct(self):
        annotation = PolygonAnnotationSetFactory(name="no oct")
        result = migrate_oct_annotations(PolygonAnnotationSet.objects.all())
        assert len(result["translated_annotations"]) == 0
        assert result["non_oct"] == [annotation.id]

    def test_migrateunmatchedocts_match(self):
        name = "oct_annotation_name"
        image = ImageFactory(modality=ImagingModalityFactory(modality="OCT"))
        annotation = PolygonAnnotationSetFactory(name=name, image=image,)
        assert ImageTextAnnotation.objects.count() == 0
        result = migrate_oct_annotations(PolygonAnnotationSet.objects.all())
        assert result["translated_annotations"] == [annotation.id]
        assert len(result["non_oct"]) == 0
        assert ImageTextAnnotation.objects.count() == 1
        assert PolygonAnnotationSet.objects.count() == 0
        text_annotation = ImageTextAnnotation.objects.first()
        assert text_annotation.grader == annotation.grader
        assert text_annotation.image == image
        assert name in text_annotation.text

    def test_migrateunmatchedocts_match_existing(self):
        name = "oct_annotation_name"
        image = ImageFactory(modality=ImagingModalityFactory(modality="OCT"))
        annotation = PolygonAnnotationSetFactory(name=name, image=image,)
        not_deleted_text = "This text should not be deleted"
        text_annotation = ImageTextAnnotationFactory(
            image=image, grader=annotation.grader, text=not_deleted_text
        )
        assert ImageTextAnnotation.objects.count() == 1
        result = migrate_oct_annotations(PolygonAnnotationSet.objects.all())
        assert result["translated_annotations"] == [annotation.id]
        assert len(result["non_oct"]) == 0
        assert ImageTextAnnotation.objects.count() == 1
        assert PolygonAnnotationSet.objects.count() == 0
        text_annotation.refresh_from_db()
        assert text_annotation.grader == annotation.grader
        assert text_annotation.image == image
        assert name in text_annotation.text
        assert not_deleted_text in text_annotation.text

    def test_migrateunmatchedocts_match_multiple_annotations(self):
        image = ImageFactory(modality=ImagingModalityFactory(modality="OCT"))
        grader = UserFactory()
        extra_kwargs = {"image": image, "grader": grader}
        annotations = (
            PolygonAnnotationSetFactory(name="annotation1", **extra_kwargs),
            PolygonAnnotationSetFactory(name="annotation2", **extra_kwargs),
            PolygonAnnotationSetFactory(name="annotation3", **extra_kwargs),
        )
        assert ImageTextAnnotation.objects.count() == 0
        result = migrate_oct_annotations(PolygonAnnotationSet.objects.all())
        assert len(result["translated_annotations"]) == 3
        assert len(result["non_oct"]) == 0
        assert ImageTextAnnotation.objects.count() == 1
        assert PolygonAnnotationSet.objects.count() == 0
        text_annotation = ImageTextAnnotation.objects.first()
        assert text_annotation.grader == grader
        assert text_annotation.image == image
        for annotation in annotations:
            assert annotation.name in text_annotation.text

    def test_migrateunmatchedocts_match_combined(self):
        non_oct_annotation = PolygonAnnotationSetFactory(name="non_oct")
        image = ImageFactory(modality=ImagingModalityFactory(modality="OCT"))
        grader = UserFactory()
        extra_kwargs = {"image": image, "grader": grader}
        image_grader_annotations = (
            PolygonAnnotationSetFactory(name="ig_annotation1", **extra_kwargs),
            PolygonAnnotationSetFactory(name="ig_annotation2", **extra_kwargs),
            PolygonAnnotationSetFactory(name="ig_annotation3", **extra_kwargs),
        )
        grader_annotations = (
            PolygonAnnotationSetFactory(
                name="grader_annotation1",
                grader=grader,
                image=ImageFactory(
                    modality=ImagingModalityFactory(modality="OCT")
                ),
            ),
            PolygonAnnotationSetFactory(
                name="grader_annotation2",
                grader=grader,
                image=ImageFactory(
                    modality=ImagingModalityFactory(modality="OCT")
                ),
            ),
        )
        image_annotations = (
            PolygonAnnotationSetFactory(
                name="image_annotation1", image=image,
            ),
            PolygonAnnotationSetFactory(
                name="image_annotation2", image=image,
            ),
        )
        not_deleted_text = "This text should not be deleted"
        existing_text_annotation = ImageTextAnnotationFactory(
            image=image,
            grader=image_annotations[0].grader,
            text=not_deleted_text,
        )
        assert ImageTextAnnotation.objects.count() == 1
        result = migrate_oct_annotations(PolygonAnnotationSet.objects.all())
        assert len(result["translated_annotations"]) == 7
        assert result["non_oct"] == [non_oct_annotation.pk]
        assert PolygonAnnotationSet.objects.count() == 1
        assert ImageTextAnnotation.objects.count() == 5
        assert ImageTextAnnotation.objects.filter(grader=grader).count() == 3
        assert ImageTextAnnotation.objects.filter(image=image).count() == 3
        text_annotation = ImageTextAnnotation.objects.get(
            grader=grader, image=image
        )
        for annotation in image_grader_annotations:
            assert annotation.name in text_annotation.text
        text_annotations = ImageTextAnnotation.objects.filter(
            grader=grader
        ).exclude(image=image)
        for text_annotation in text_annotations:
            assert (
                grader_annotations[0].name in text_annotation.text
                or grader_annotations[1].name in text_annotation.text
            )
        text_annotations = ImageTextAnnotation.objects.filter(
            image=image
        ).exclude(grader=grader)
        for text_annotation in text_annotations:
            assert (
                image_annotations[0].name in text_annotation.text
                or image_annotations[1].name in text_annotation.text
            )
        existing_text_annotation.refresh_from_db()
        assert not_deleted_text in existing_text_annotation.text
        assert image_annotations[0].name in existing_text_annotation.text
