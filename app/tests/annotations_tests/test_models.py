import pytest
from django.db import IntegrityError

from tests.annotations_tests.factories import (
    ETDRSGridAnnotationFactory,
    MeasurementAnnotationFactory,
)


@pytest.mark.django_db
class TestAnnotationModels:
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
            # Duplicate the creation
            MeasurementAnnotationFactory(
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
