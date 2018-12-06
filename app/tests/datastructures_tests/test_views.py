import pytest
from tests.retina_images_tests.factories import RetinaImageFactory
from tests.studies_tests.factories import StudyFactory
from tests.patients_tests.factories import PatientFactory
from tests.archives_tests.factories import ArchiveFactory
from grandchallenge.archives.views import ArchiveViewSet
from grandchallenge.patients.views import PatientViewSet
from grandchallenge.studies.views import StudyViewSet

from grandchallenge.archives.serializers import ArchiveSerializer
from grandchallenge.patients.serializers import PatientSerializer
from grandchallenge.studies.serializers import StudySerializer
from tests.studies_tests.test_views import required_relations

from tests.viewset_helpers import batch_test_viewset_endpoints, VIEWSET_ACTIONS


@pytest.mark.django_db
class TestViewsets:
    # test functions are added dynamically to this class
    def test_empty(self):
        assert True
    pass


actions = VIEWSET_ACTIONS
# Add all model viewset test functions to class
required_relations = {"images": [RetinaImageFactory]}
batch_test_viewset_endpoints(
    actions,
    ArchiveViewSet,
    "archive",
    ArchiveFactory,
    TestViewsets,
    required_relations,
    serializer=ArchiveSerializer,
)

# required_relations = {"archive": ArchiveFactory}
batch_test_viewset_endpoints(
    actions,
    PatientViewSet,
    "patient",
    PatientFactory,
    TestViewsets,
    # required_relations,
    serializer=PatientSerializer,
)


#
# required_relations = {"study": StudyFactory}
# batch_test_viewset_endpoints(
#     actions,
#     SeriesViewSet,
#     "series",
#     SeriesFactory,
#     TestViewsets,
#     required_relations,
#     serializer=SeriesSerializer,
# )


