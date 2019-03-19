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
)
from tests.serializer_helpers import batch_test_serializers


@pytest.mark.django_db
class TestAnnotationSerializers:
    # test methods are added dynamically to this class, see below
    pass


serializers = {
    "etdrs": {
        "unique": True,
        "factory": ETDRSGridAnnotationFactory,
        "serializer": ETDRSGridAnnotationSerializer,
        "fields": ("grader", "created", "image", "fovea", "optic_disk"),
    },
    "measurement": {
        "unique": True,
        "factory": MeasurementAnnotationFactory,
        "serializer": MeasurementAnnotationSerializer,
        "fields": ("image", "grader", "created", "start_voxel", "end_voxel"),
    },
    "boolean": {
        "unique": True,
        "factory": BooleanClassificationAnnotationFactory,
        "serializer": BooleanClassificationAnnotationSerializer,
        "fields": ("image", "grader", "created", "name", "value"),
    },
    "polygon": {
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
    "single_polygon": {
        "unique": True,
        "factory": SinglePolygonAnnotationFactory,
        "serializer": SinglePolygonAnnotationSerializer,
        "fields": ("id", "value", "annotation_set"),
    },
    "landmark": {
        "unique": True,
        "factory": LandmarkAnnotationSetFactory,
        "serializer": LandmarkAnnotationSetSerializer,
        "fields": ("grader", "created"),
    },
}

batch_test_serializers(serializers, TestAnnotationSerializers)
