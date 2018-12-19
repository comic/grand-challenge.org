import pytest
from tests.retina_images_tests.factories import ImageFactoryWithImageFile
from tests.studies_tests.factories import StudyFactory
from tests.viewset_helpers import batch_test_viewset_endpoints, VIEWSET_ACTIONS
from grandchallenge.cases.views import ImageViewSet
from grandchallenge.cases.serializers import ImageSerializer


# Currently the ImageViewSet is defined in cases/views.py but not implemented in cases/urls.py
# Therefore, these tests are commented out
# TODO move these tests to cases/test_views.py when immplemented
#
# @pytest.mark.django_db
# class TestViewsets:
#     # test functions are added dynamically to this class
#     pass
#
#
# actions = VIEWSET_ACTIONS
#
# image_actions = actions[:2]
# required_relations = {"study": StudyFactory}
# # skip create and update for image because viewset is readonly
# batch_test_viewset_endpoints(
#     image_actions,
#     ImageViewSet,
#     "image",
#     "cases",
#     ImageFactoryWithImageFile,
#     TestViewsets,
#     required_relations,
#     serializer=ImageSerializer,
# )