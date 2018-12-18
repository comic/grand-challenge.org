import pytest
from tests.retina_images_tests.factories import ImageFactoryWithImageFile
from tests.studies_tests.factories import StudyFactory
from tests.viewset_helpers import batch_test_viewset_endpoints, VIEWSET_ACTIONS
from grandchallenge.cases.views import ImageViewSet
from grandchallenge.cases.serializers import ImageSerializer


@pytest.mark.django_db
class TestCustomEndpoints:
    pass


@pytest.mark.django_db
class TestViewsets:
    # test functions are added dynamically to this class
    pass


actions = VIEWSET_ACTIONS

image_actions = actions[:3]
required_relations = {"study": StudyFactory}
# skip create and update for image because no image file can be made.
batch_test_viewset_endpoints(
    image_actions,
    ImageViewSet,
    "image",
    "cases",
    ImageFactoryWithImageFile,
    TestViewsets,
    required_relations,
    serializer=ImageSerializer,
)