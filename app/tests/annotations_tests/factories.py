import datetime

import factory.fuzzy
import pytz

from grandchallenge.annotations.models import (
    AbstractImageAnnotationModel,
    AbstractNamedImageAnnotationModel,
    BooleanClassificationAnnotation,
    CoordinateListAnnotation,
    ETDRSGridAnnotation,
    ImagePathologyAnnotation,
    ImageQualityAnnotation,
    ImageTextAnnotation,
    IntegerClassificationAnnotation,
    LandmarkAnnotationSet,
    MeasurementAnnotation,
    PolygonAnnotationSet,
    RetinaImagePathologyAnnotation,
    SingleLandmarkAnnotation,
    SinglePolygonAnnotation,
)
from tests.cases_tests.factories import ImageFactory
from tests.factories import FuzzyFloatCoordinatesList, UserFactory


class DefaultImageAnnotationModelFactory(factory.DjangoModelFactory):
    class Meta:
        model = AbstractImageAnnotationModel
        abstract = True

    image = factory.SubFactory(ImageFactory)
    grader = factory.SubFactory(UserFactory)
    created = factory.fuzzy.FuzzyDateTime(
        datetime.datetime(1950, 1, 1, 0, 0, 0, 0, pytz.UTC)
    )


class ETDRSGridAnnotationFactory(DefaultImageAnnotationModelFactory):
    class Meta:
        model = ETDRSGridAnnotation

    fovea = FuzzyFloatCoordinatesList(1)
    optic_disk = FuzzyFloatCoordinatesList(1)


class MeasurementAnnotationFactory(DefaultImageAnnotationModelFactory):
    class Meta:
        model = MeasurementAnnotation

    start_voxel = FuzzyFloatCoordinatesList(1)
    end_voxel = FuzzyFloatCoordinatesList(1)


class DefaultNamedImageAnnotationModelFactory(
    DefaultImageAnnotationModelFactory
):
    class Meta:
        model = AbstractNamedImageAnnotationModel
        abstract = True

    name = factory.fuzzy.FuzzyText()


class BooleanClassificationAnnotationFactory(
    DefaultNamedImageAnnotationModelFactory
):
    class Meta:
        model = BooleanClassificationAnnotation

    value = factory.fuzzy.FuzzyChoice([True, False])


class IntegerClassificationAnnotationFactory(
    DefaultNamedImageAnnotationModelFactory
):
    class Meta:
        model = IntegerClassificationAnnotation

    value = factory.fuzzy.FuzzyInteger(1000)


class CoordinateListAnnotationFactory(DefaultNamedImageAnnotationModelFactory):
    class Meta:
        model = CoordinateListAnnotation

    value = FuzzyFloatCoordinatesList()


class PolygonAnnotationSetFactory(DefaultNamedImageAnnotationModelFactory):
    class Meta:
        model = PolygonAnnotationSet


class SinglePolygonAnnotationFactory(factory.DjangoModelFactory):
    class Meta:
        model = SinglePolygonAnnotation

    annotation_set = factory.SubFactory(PolygonAnnotationSetFactory)

    value = FuzzyFloatCoordinatesList()


class LandmarkAnnotationSetFactory(factory.DjangoModelFactory):
    class Meta:
        model = LandmarkAnnotationSet

    grader = factory.SubFactory(UserFactory)
    created = factory.fuzzy.FuzzyDateTime(
        datetime.datetime(1950, 1, 1, 0, 0, 0, 0, pytz.UTC)
    )


class SingleLandmarkAnnotationFactory(factory.DjangoModelFactory):
    class Meta:
        model = SingleLandmarkAnnotation

    image = factory.SubFactory(ImageFactory)
    annotation_set = factory.SubFactory(LandmarkAnnotationSetFactory)

    landmarks = FuzzyFloatCoordinatesList()


class ImageQualityAnnotationFactory(DefaultImageAnnotationModelFactory):
    class Meta:
        model = ImageQualityAnnotation

    quality = factory.Iterator(
        [x[0] for x in ImageQualityAnnotation.QUALITY_CHOICES]
    )
    quality_reason = factory.Iterator(
        [x[0] for x in ImageQualityAnnotation.QUALITY_REASON_CHOICES]
    )


class ImagePathologyAnnotationFactory(DefaultImageAnnotationModelFactory):
    class Meta:
        model = ImagePathologyAnnotation

    pathology = factory.Iterator(
        [x[0] for x in ImagePathologyAnnotation.PATHOLOGY_CHOICES]
    )


class RetinaImagePathologyAnnotationFactory(
    DefaultImageAnnotationModelFactory
):
    class Meta:
        model = RetinaImagePathologyAnnotation

    amd_present = factory.fuzzy.FuzzyChoice([True, False])
    dr_present = factory.fuzzy.FuzzyChoice([True, False])
    oda_present = factory.fuzzy.FuzzyChoice([True, False])
    myopia_present = factory.fuzzy.FuzzyChoice([True, False])
    cysts_present = factory.fuzzy.FuzzyChoice([True, False])
    other_present = factory.fuzzy.FuzzyChoice([True, False])


class ImageTextAnnotationFactory(DefaultImageAnnotationModelFactory):
    class Meta:
        model = ImageTextAnnotation

    text = factory.fuzzy.FuzzyText(prefix="Random text - ")
