import pytest
from tests.retina_images_tests.factories import ImageFactory
from grandchallenge.archives.views import ArchiveViewSet
from tests.archives_tests.factories import ArchiveFactory
from grandchallenge.archives.serializers import ArchiveSerializer
from tests.viewset_helpers import batch_test_viewset_endpoints, VIEWSET_ACTIONS


@pytest.mark.django_db
class TestViewsets:
    # test functions are added dynamically to this class
    pass


required_relations = {"images": [ImageFactory]}
batch_test_viewset_endpoints(
    VIEWSET_ACTIONS,
    ArchiveViewSet,
    "archive",
    "archives",
    ArchiveFactory,
    TestViewsets,
    required_relations,
    serializer=ArchiveSerializer,
)
