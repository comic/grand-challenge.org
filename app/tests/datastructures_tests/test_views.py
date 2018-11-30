import pytest
from django.urls import reverse
from rest_framework import status
from PIL import Image as PILImage
import numpy as np
import io
from tests.datastructures_tests.factories import (
    ArchiveFactory,
    PatientFactory,
    StudyFactory,
    RetinaImageFactory,
    create_oct_series,
)
from grandchallenge.archives.views import ArchiveViewSet
from grandchallenge.patients.views import PatientViewSet
from grandchallenge.studies.views import StudyViewSet
from grandchallenge.retina_images.views import RetinaImageViewSet

from grandchallenge.archives.serializers import ArchiveSerializer
from grandchallenge.patients.serializers import PatientSerializer
from grandchallenge.studies.serializers import StudySerializer
from grandchallenge.retina_images.serializers import RetinaImageSerializer

from tests.viewset_helpers import batch_test_viewset_endpoints, VIEWSET_ACTIONS, TEST_USER_CREDENTIALS
from grandchallenge.retina_images.models import RetinaImage


@pytest.mark.django_db
class TestCustomEndpoints:
    def test_thumbnail_endpoint_non_authenticated(self, client):
        image = RetinaImageFactory()
        url = reverse("retina:image-thumbnail", args=[image.id])
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_thumbnail_endpoint_authenticated_non_existant(self, client, django_user_model):
        image = RetinaImageFactory()
        url = reverse("retina:image-thumbnail", args=[image.id])
        django_user_model.objects.create_user(**TEST_USER_CREDENTIALS)
        client.login(**TEST_USER_CREDENTIALS)
        image.delete()  # remove model so response must return 404
        response = client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_thumbnail_endpoint_authenticated(self, client, django_user_model):
        image = RetinaImageFactory()
        url = reverse("retina:image-thumbnail", args=[image.id])
        django_user_model.objects.create_user(**TEST_USER_CREDENTIALS)
        client.login(**TEST_USER_CREDENTIALS)
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-type"] == "image/png"

        response_np = np.array(PILImage.open(io.BytesIO(response.content)))
        request_np = np.array(PILImage.open(image.image.path))
        assert np.array_equal(response_np, request_np)

    def test_numpy_endpoint_non_authenticated(self, client):
        image = RetinaImageFactory()
        url = reverse("retina:image-numpy", args=[image.id])
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_numpy_endpoint_authenticated_non_existant(self, client, django_user_model):
        image = RetinaImageFactory()
        url = reverse("retina:image-numpy", args=[image.id])
        django_user_model.objects.create_user(**TEST_USER_CREDENTIALS)
        client.login(**TEST_USER_CREDENTIALS)
        image.delete()  # remove model so response must return 404
        response = client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_numpy_endpoint_authenticated_status(self, client, django_user_model):
        image = RetinaImageFactory()
        url = reverse("retina:image-numpy", args=[image.id])
        django_user_model.objects.create_user(**TEST_USER_CREDENTIALS)
        client.login(**TEST_USER_CREDENTIALS)
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-type"] == "application/octet-stream"

    def test_numpy_endpoint_authenticated_images_correspond(self, client, django_user_model):
        image = RetinaImageFactory(modality=RetinaImage.MODALITY_CF)
        url = reverse("retina:image-numpy", args=[image.id])
        django_user_model.objects.create_user(**TEST_USER_CREDENTIALS)
        client.login(**TEST_USER_CREDENTIALS)
        response = client.get(url)
        response_np = np.load(io.BytesIO(response.content))
        request_image_arr = np.array(PILImage.open(image.image.path))
        assert np.array_equal(response_np, request_image_arr)

    def test_numpy_endpoint_authenticated_oct_series_status(self, client, django_user_model):
        series_oct, images_oct = create_oct_series()
        url = reverse("retina:image-numpy", args=[images_oct[0].id])
        django_user_model.objects.create_user(**TEST_USER_CREDENTIALS)
        client.login(**TEST_USER_CREDENTIALS)
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-type"] == "application/octet-stream"

    def test_numpy_endpoint_authenticated_oct_series_image_count(self, client, django_user_model):
        series_oct, images_oct = create_oct_series()
        url = reverse("retina:image-numpy", args=[images_oct[0].id])
        django_user_model.objects.create_user(**TEST_USER_CREDENTIALS)
        client.login(**TEST_USER_CREDENTIALS)
        response = client.get(url)
        response_np = np.load(io.BytesIO(response.content))
        assert response_np.shape[0] == len(images_oct)

    def test_numpy_endpoint_authenticated_oct_series_images_corresond(self, client, django_user_model):
        series_oct, images_oct = create_oct_series()
        url = reverse("retina:image-numpy", args=[images_oct[0].id])
        django_user_model.objects.create_user(**TEST_USER_CREDENTIALS)
        client.login(**TEST_USER_CREDENTIALS)
        response = client.get(url)

        request_np_images = [np.array(PILImage.open(x.image.path)) for x in images_oct]
        response_np = np.load(io.BytesIO(response.content))
        for np_image in response_np:
            image_in_array = False
            for np_request_image in request_np_images:
                if np.array_equal(np_image, np_request_image):
                    image_in_array = True

            if not image_in_array:
                pytest.fail("request OCT images do not match response images")
                break



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

required_relations = {"patient": PatientFactory}
batch_test_viewset_endpoints(
    actions,
    StudyViewSet,
    "study",
    StudyFactory,
    TestViewsets,
    required_relations,
    serializer=StudySerializer,
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

# skip create and update for image because no image file can be made.
image_actions = actions[:3]
required_relations = {"study": StudyFactory}
batch_test_viewset_endpoints(
    image_actions,
    RetinaImageViewSet,
    "retinaimage",
    RetinaImageFactory,
    TestViewsets,
    required_relations,
    serializer=RetinaImageSerializer,
)
