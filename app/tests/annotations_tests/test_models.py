import pytest
from tests.annotations_tests.factories import (
    ETDRSGridAnnotationFactory,
    MeasurementAnnotationFactory,
    BooleanClassificationAnnotationFactory,
    IntegerClassificationAnnotationFactory,
    CoordinateListAnnotationFactory,
    PolygonAnnotationSetFactory,
    SinglePolygonAnnotationFactory,
    LandmarkAnnotationSetFactory,
    SingleLandmarkAnnotationFactory,
)
from tests.model_helpers import batch_test_factories
from django.db import IntegrityError


@pytest.mark.django_db
class TestAnnotationModels:
    # test functions are added dynamically to this class

    def test_default_model_str(self):
        etdrs = ETDRSGridAnnotationFactory()
        assert str(etdrs) == "<{} by {} on {} for {}>".format(
            etdrs.__class__.__name__,
            etdrs.grader.username,
            etdrs.created.strftime("%Y-%m-%d at %H:%M:%S"),
            etdrs.image,
        )

    def test_measurement_duplicate_not_allowed(self):
        measurement = MeasurementAnnotationFactory()
        try:
            measuremt_duplicate = MeasurementAnnotationFactory(
                image=measurement.image,
                grader=measurement.grader,
                created=measurement.created,
                start_voxel=measurement.start_voxel,
                end_voxel=measurement.end_voxel,
            )
            pytest.fail(
                "No integrity error when submitting duplicate measurement annotation"
            )
        except IntegrityError:
            pass


factories = {
    "etdrs": ETDRSGridAnnotationFactory,
    "measurement": MeasurementAnnotationFactory,
    "boolean": BooleanClassificationAnnotationFactory,
    "integer": IntegerClassificationAnnotationFactory,
    "coordinates": CoordinateListAnnotationFactory,
    "polygonset": PolygonAnnotationSetFactory,
    "singlepolygon": SinglePolygonAnnotationFactory,
    "landmarkset": LandmarkAnnotationSetFactory,
    "singlelandmark": SingleLandmarkAnnotationFactory,
}
batch_test_factories(factories, TestAnnotationModels)
