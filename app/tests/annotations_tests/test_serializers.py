import pytest

from grandchallenge.annotations.serializers import (
    BooleanClassificationAnnotationSerializer,
    ETDRSGridAnnotationSerializer,
    ImagePathologyAnnotationSerializer,
    ImageQualityAnnotationSerializer,
    ImageTextAnnotationSerializer,
    LandmarkAnnotationSetSerializer,
    MeasurementAnnotationSerializer,
    PolygonAnnotationSetSerializer,
    RetinaImagePathologyAnnotationSerializer,
    SingleLandmarkAnnotationSerializer,
    SinglePolygonAnnotationSerializer,
)
from tests.annotations_tests.factories import (
    BooleanClassificationAnnotationFactory,
    ETDRSGridAnnotationFactory,
    ImagePathologyAnnotationFactory,
    ImageQualityAnnotationFactory,
    ImageTextAnnotationFactory,
    LandmarkAnnotationSetFactory,
    MeasurementAnnotationFactory,
    PolygonAnnotationSetFactory,
    RetinaImagePathologyAnnotationFactory,
    SingleLandmarkAnnotationFactory,
    SinglePolygonAnnotationFactory,
)
from tests.serializer_helpers import (
    do_test_serializer_fields,
    do_test_serializer_valid,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "serializer_data",
    (
        (
            {
                "unique": True,
                "factory": ETDRSGridAnnotationFactory,
                "serializer": ETDRSGridAnnotationSerializer,
                "fields": (
                    "id",
                    "grader",
                    "created",
                    "image",
                    "fovea",
                    "optic_disk",
                ),
            },
            {
                "unique": True,
                "factory": MeasurementAnnotationFactory,
                "serializer": MeasurementAnnotationSerializer,
                "fields": (
                    "image",
                    "grader",
                    "created",
                    "start_voxel",
                    "end_voxel",
                ),
            },
            {
                "unique": True,
                "factory": BooleanClassificationAnnotationFactory,
                "serializer": BooleanClassificationAnnotationSerializer,
                "fields": ("image", "grader", "created", "name", "value"),
            },
            {
                "unique": True,
                "factory": PolygonAnnotationSetFactory,
                "serializer": PolygonAnnotationSetSerializer,
                "fields": (
                    "id",
                    "image",
                    "grader",
                    "created",
                    "name",
                    "singlepolygonannotation_set",
                ),
            },
            {
                "unique": True,
                "factory": SinglePolygonAnnotationFactory,
                "serializer": SinglePolygonAnnotationSerializer,
                "fields": (
                    "id",
                    "value",
                    "annotation_set",
                    "created",
                    "x_axis_orientation",
                    "y_axis_orientation",
                    "z",
                ),
            },
            {
                "unique": True,
                "factory": LandmarkAnnotationSetFactory,
                "serializer": LandmarkAnnotationSetSerializer,
                "fields": (
                    "id",
                    "grader",
                    "created",
                    "singlelandmarkannotation_set",
                ),
            },
            {
                "unique": True,
                "factory": SingleLandmarkAnnotationFactory,
                "serializer": SingleLandmarkAnnotationSerializer,
                "fields": ("image", "annotation_set", "landmarks"),
            },
            {
                "unique": True,
                "factory": ImageQualityAnnotationFactory,
                "serializer": ImageQualityAnnotationSerializer,
                "fields": (
                    "id",
                    "created",
                    "grader",
                    "image",
                    "quality",
                    "quality_reason",
                ),
            },
            {
                "unique": True,
                "factory": ImagePathologyAnnotationFactory,
                "serializer": ImagePathologyAnnotationSerializer,
                "fields": ("id", "created", "grader", "image", "pathology"),
            },
            {
                "unique": True,
                "factory": RetinaImagePathologyAnnotationFactory,
                "serializer": RetinaImagePathologyAnnotationSerializer,
                "fields": (
                    "id",
                    "grader",
                    "created",
                    "image",
                    "amd_present",
                    "dr_present",
                    "oda_present",
                    "myopia_present",
                    "cysts_present",
                    "other_present",
                ),
            },
            {
                "unique": True,
                "factory": ImageTextAnnotationFactory,
                "serializer": ImageTextAnnotationSerializer,
                "fields": ("id", "grader", "created", "image", "text"),
            },
        )
    ),
)
class TestSerializers:
    def test_serializer_valid(self, serializer_data):
        do_test_serializer_valid(serializer_data)

    def test_serializer_fields(self, serializer_data):
        do_test_serializer_fields(serializer_data)
