import datetime

import factory.fuzzy

from grandchallenge.annotations.models import (
    AbstractImageAnnotationModel,
    ETDRSGridAnnotation,
    MeasurementAnnotation,
)
from tests.cases_tests.factories import ImageFactory
from tests.factories import FuzzyFloatCoordinatesList, UserFactory


class DefaultImageAnnotationModelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AbstractImageAnnotationModel
        abstract = True

    image = factory.SubFactory(ImageFactory)
    grader = factory.SubFactory(UserFactory)
    created = factory.fuzzy.FuzzyDateTime(
        datetime.datetime(1950, 1, 1, 0, 0, 0, 0, datetime.timezone.utc)
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
