import io

import numpy as np
import pytest
from PIL import Image as PILImage
from django.urls import reverse
from rest_framework import status
import SimpleITK as sitk

from tests.retina_images_tests.factories import ImageFactoryWithImageFile
from grandchallenge.challenges.models import ImagingModality
from tests.retina_core_tests.factories import create_oct_series
from tests.studies_tests.factories import StudyFactory
from tests.viewset_helpers import TEST_USER_CREDENTIALS
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
    ImageFactoryWithImageFile,
    TestViewsets,
    required_relations,
    serializer=ImageSerializer,
)