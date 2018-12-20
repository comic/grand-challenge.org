import random
import factory
import factory.fuzzy
import datetime
import pytz
from grandchallenge.annotations.models import (
    AbstractImageAnnotationModel,
    AbstractNamedImageAnnotationModel,
    ETDRSGridAnnotation,
    MeasurementAnnotation,
    BooleanClassificationAnnotation,
    IntegerClassificationAnnotation,
    CoordinateListAnnotation,
    PolygonAnnotationSet,
    SinglePolygonAnnotation,
    LandmarkAnnotationSet,
    SingleLandmarkAnnotation,
)
from tests.retina_images_tests.factories import ImageFactory
from tests.factories import UserFactory


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

    fovea = [random.uniform(0.0, 50.0), random.uniform(0.0, 50.0)]
    optic_disk = [random.uniform(0.0, 50.0), random.uniform(0.0, 50.0)]


class MeasurementAnnotationFactory(DefaultImageAnnotationModelFactory):
    class Meta:
        model = MeasurementAnnotation

    start_voxel = [random.uniform(0.0, 50.0), random.uniform(0.0, 50.0)]
    end_voxel = [random.uniform(0.0, 50.0), random.uniform(0.0, 50.0)]


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

    value = [
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
    ]


class PolygonAnnotationSetFactory(DefaultNamedImageAnnotationModelFactory):
    class Meta:
        model = PolygonAnnotationSet


class SinglePolygonAnnotationFactory(factory.DjangoModelFactory):
    class Meta:
        model = SinglePolygonAnnotation

    annotation_set = factory.SubFactory(PolygonAnnotationSetFactory)

    value = [
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
    ]


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

    landmarks = [
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
        [random.uniform(0.0, 1000.0), random.uniform(0.0, 1000.0)],
    ]


def create_batch_landmarks():
    landmark_annotation_set = LandmarkAnnotationSet()
    landmark_annotations = []
    for i in range(3):
        landmark_annotations.append(
            SingleLandmarkAnnotationFactory(
                registration=landmark_annotation_set
            )
        )

    return landmark_annotation_set, landmark_annotations
