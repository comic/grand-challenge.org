import pytest
from rest_framework import status
from tests.annotations_tests.factories import (
    ETDRSGridAnnotationFactory,
    MeasurementAnnotationFactory,
    BooleanClassificationAnnotationFactory,
    IntegerClassificationAnnotationFactory,
    CoordinateListAnnotationFactory,
    PolygonAnnotationSetFactory,
    SinglePolygonAnnotationFactory,
    LandmarkAnnotationSetFactory,
)
from tests.retina_images_tests.factories import RetinaImageFactory
from tests.factories import UserFactory
from grandchallenge.annotations.views import (
    ETDRSGridAnnotationViewSet,
    MeasurementAnnotationViewSet,
    BooleanClassificationAnnotationViewSet,
    PolygonAnnotationSetViewSet,
    LandmarkAnnotationSetViewSet,
)
from grandchallenge.annotations.serializers import (
    ETDRSGridAnnotationSerializer,
    MeasurementAnnotationSerializer,
    BooleanClassificationAnnotationSerializer,
    PolygonAnnotationSetSerializer,
    LandmarkAnnotationSetSerializer,
)
from tests.viewset_helpers import batch_test_viewset_endpoints, VIEWSET_ACTIONS


@pytest.mark.django_db
class TestViewsets:
    # test functions are added dynamically to this class
    pass


actions = VIEWSET_ACTIONS
# Add all model viewset test functions to class
required_relations = {"image": RetinaImageFactory, "grader": UserFactory}
batch_test_viewset_endpoints(
    actions,
    ETDRSGridAnnotationViewSet,
    "etdrsgridannotation",
    ETDRSGridAnnotationFactory,
    TestViewsets,
    required_relations,
    serializer=ETDRSGridAnnotationSerializer,
)
batch_test_viewset_endpoints(
    actions,
    MeasurementAnnotationViewSet,
    "measurementannotation",
    MeasurementAnnotationFactory,
    TestViewsets,
    required_relations,
    serializer=MeasurementAnnotationSerializer
)

batch_test_viewset_endpoints(
    actions,
    BooleanClassificationAnnotationViewSet,
    "booleanclassificationannotation",
    BooleanClassificationAnnotationFactory,
    TestViewsets,
    required_relations,
    serializer=BooleanClassificationAnnotationSerializer
)

batch_test_viewset_endpoints(
    actions,
    PolygonAnnotationSetViewSet,
    "polygonannotationset",
    PolygonAnnotationSetFactory,
    TestViewsets,
    required_relations,
    serializer=PolygonAnnotationSetSerializer
)

required_relations = {"grader": UserFactory}
batch_test_viewset_endpoints(
    actions,
    LandmarkAnnotationSetViewSet,
    "landmarkannotationset",
    LandmarkAnnotationSetFactory,
    TestViewsets,
    required_relations,
    serializer=LandmarkAnnotationSetSerializer
)
