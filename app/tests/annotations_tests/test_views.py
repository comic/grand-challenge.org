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
from tests.retina_images_tests.factories import ImageFactory
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
namespace = "annotations"
# Add all model viewset test functions to class
required_relations = {"image": ImageFactory, "grader": UserFactory}
batch_test_viewset_endpoints(
    actions,
    ETDRSGridAnnotationViewSet,
    "etdrsgridannotation",
    namespace,
    ETDRSGridAnnotationFactory,
    TestViewsets,
    required_relations,
    serializer=ETDRSGridAnnotationSerializer,
)
batch_test_viewset_endpoints(
    actions,
    MeasurementAnnotationViewSet,
    "measurementannotation",
    namespace,
    MeasurementAnnotationFactory,
    TestViewsets,
    required_relations,
    serializer=MeasurementAnnotationSerializer,
)

batch_test_viewset_endpoints(
    actions,
    BooleanClassificationAnnotationViewSet,
    "booleanclassificationannotation",
    namespace,
    BooleanClassificationAnnotationFactory,
    TestViewsets,
    required_relations,
    serializer=BooleanClassificationAnnotationSerializer,
)

batch_test_viewset_endpoints(
    actions,
    PolygonAnnotationSetViewSet,
    "polygonannotationset",
    namespace,
    PolygonAnnotationSetFactory,
    TestViewsets,
    required_relations,
    serializer=PolygonAnnotationSetSerializer,
)

required_relations = {"grader": UserFactory}
batch_test_viewset_endpoints(
    actions,
    LandmarkAnnotationSetViewSet,
    "landmarkannotationset",
    namespace,
    LandmarkAnnotationSetFactory,
    TestViewsets,
    required_relations,
    serializer=LandmarkAnnotationSetSerializer,
)
