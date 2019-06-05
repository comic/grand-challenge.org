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
from grandchallenge.annotations.serializers import (
    ETDRSGridAnnotationSerializer,
    MeasurementAnnotationSerializer,
    BooleanClassificationAnnotationSerializer,
    PolygonAnnotationSetSerializer,
    LandmarkAnnotationSetSerializer,
    SinglePolygonAnnotationSerializer,
    SingleLandmarkAnnotationSerializer,
)
from tests.serializer_helpers import (
    do_test_serializer_valid,
    do_test_serializer_fields,
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
                "fields": ("id", "value", "annotation_set", "created"),
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
        )
    ),
)
class TestSerializers:
    def test_serializer_valid(self, serializer_data):
        do_test_serializer_valid(serializer_data)

    def test_serializer_fields(self, serializer_data):
        do_test_serializer_fields(serializer_data)
