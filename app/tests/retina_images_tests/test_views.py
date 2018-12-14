import io

import numpy as np
import pytest
from PIL import Image as PILImage
from django.urls import reverse
from rest_framework import status
import SimpleITK as sitk

from grandchallenge.retina_images.models import RetinaImage
from tests.retina_images_tests.factories import RetinaImageFactory
from tests.retina_core_tests.factories import create_oct_series
from tests.studies_tests.factories import StudyFactory
from tests.viewset_helpers import TEST_USER_CREDENTIALS
from tests.viewset_helpers import batch_test_viewset_endpoints, VIEWSET_ACTIONS
from grandchallenge.retina_images.views import RetinaImageViewSet
from grandchallenge.retina_images.serializers import RetinaImageSerializer


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

        response_np = np.array(PILImage.open(io.BytesIO(response.content)), np.uint8)
        sitk_image = image.get_sitk_image()
        depth = sitk_image.GetDepth()
        nda_image = sitk.GetArrayFromImage(sitk_image)
        if depth > 0:
            nda_image = nda_image[depth // 2]
        expected_np = nda_image.astype(np.uint8)
        assert np.array_equal(response_np, expected_np)

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
        sitk_image = image.get_sitk_image()
        nda_image = sitk.GetArrayFromImage(sitk_image)
        request_image_arr = nda_image.astype(np.uint8)
        assert np.array_equal(response_np, request_image_arr)

    def test_numpy_endpoint_authenticated_oct_series_status(self, client, django_user_model):
        series_oct, images_oct = create_oct_series()
        url = reverse("retina:image-numpy", args=[images_oct[0].id])
        django_user_model.objects.create_user(**TEST_USER_CREDENTIALS)
        client.login(**TEST_USER_CREDENTIALS)
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-type"] == "application/octet-stream"

    def test_numpy_endpoint_authenticated_oct_series_z_count(self, client, django_user_model):
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
    pass


actions = VIEWSET_ACTIONS

image_actions = actions[:3]
required_relations = {"study": StudyFactory}
# skip create and update for image because no image file can be made.
batch_test_viewset_endpoints(
    image_actions,
    RetinaImageViewSet,
    "retinaimage",
    RetinaImageFactory,
    TestViewsets,
    required_relations,
    serializer=RetinaImageSerializer,
)