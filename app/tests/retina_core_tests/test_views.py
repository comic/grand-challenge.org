import pytest
import io
import numpy as np
import SimpleITK as sitk
from PIL import Image as PILImage
from rest_framework import status
from grandchallenge.subdomains.urls import reverse
from django.urls import reverse as django_reverse
from tests.retina_importers_tests.helpers import get_auth_token_header, get_user_with_token
from django.conf import settings
from tests.retina_images_tests.factories import ImageFactoryWithImageFile
from tests.viewset_helpers import TEST_USER_CREDENTIALS
from grandchallenge.challenges.models import ImagingModality

@pytest.mark.django_db
class TestTokenAuthentication:
    def test_no_auth(self, client):
        url = reverse("retina:home")
        response = client.get(url, follow=True)

        assert response.redirect_chain[0][1] == status.HTTP_302_FOUND
        assert (
            settings.LOGIN_URL + "?next=" + django_reverse("retina:home")
            == response.redirect_chain[0][0]
        )
        assert status.HTTP_200_OK == response.status_code

    def test_auth_normal(self, client):
        url = reverse("retina:home")
        user, token = get_user_with_token()
        client.force_login(user=user)
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_auth_staff(self, client):
        url = reverse("retina:home")
        user, token = get_user_with_token()
        client.force_login(user=user)
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    # TODO add retina user test

@pytest.mark.django_db
class TestCustomImageViews:
    def test_thumbnail_endpoint_non_authenticated(self, client):
        image = ImageFactoryWithImageFile()
        url = reverse("retina:image-thumbnail", args=[image.id])
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_thumbnail_endpoint_authenticated_non_existant(self, client, django_user_model):
        image = ImageFactoryWithImageFile()
        url = reverse("retina:image-thumbnail", args=[image.id])
        django_user_model.objects.create_user(**TEST_USER_CREDENTIALS)
        client.login(**TEST_USER_CREDENTIALS)
        image.delete()  # remove model so response must return 404
        response = client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_thumbnail_endpoint_authenticated(self, client, django_user_model):
        image = ImageFactoryWithImageFile()
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
        image = ImageFactoryWithImageFile()
        url = reverse("retina:image-numpy", args=[image.id])
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_numpy_endpoint_authenticated_non_existant(self, client, django_user_model):
        image = ImageFactoryWithImageFile()
        url = reverse("retina:image-numpy", args=[image.id])
        django_user_model.objects.create_user(**TEST_USER_CREDENTIALS)
        client.login(**TEST_USER_CREDENTIALS)
        image.delete()  # remove model so response must return 404
        response = client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_numpy_endpoint_authenticated_status(self, client, django_user_model):
        image = ImageFactoryWithImageFile()
        url = reverse("retina:image-numpy", args=[image.id])
        django_user_model.objects.create_user(**TEST_USER_CREDENTIALS)
        client.login(**TEST_USER_CREDENTIALS)
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-type"] == "application/octet-stream"

    def test_numpy_endpoint_authenticated_images_correspond(self, client, django_user_model):
        image = ImageFactoryWithImageFile(modality__modality=ImagingModality.MODALITY_CF)
        url = reverse("retina:image-numpy", args=[image.id])
        django_user_model.objects.create_user(**TEST_USER_CREDENTIALS)
        client.login(**TEST_USER_CREDENTIALS)
        response = client.get(url)
        response_np = np.load(io.BytesIO(response.content))
        sitk_image = image.get_sitk_image()
        nda_image = sitk.GetArrayFromImage(sitk_image)
        request_image_arr = nda_image.astype(np.int8)
        assert np.array_equal(response_np, request_image_arr)

    # def test_numpy_endpoint_authenticated_oct_series_status(self, client, django_user_model):
    #     series_oct, images_oct = create_oct_series()
    #     url = reverse("retina:image-numpy", args=[images_oct[0].id])
    #     django_user_model.objects.create_user(**TEST_USER_CREDENTIALS)
    #     client.login(**TEST_USER_CREDENTIALS)
    #     response = client.get(url)
    #     assert response.status_code == status.HTTP_200_OK
    #     assert response["Content-type"] == "application/octet-stream"
    #
    # def test_numpy_endpoint_authenticated_oct_series_z_count(self, client, django_user_model):
    #     series_oct, images_oct = create_oct_series()
    #     url = reverse("retina:image-numpy", args=[images_oct[0].id])
    #     django_user_model.objects.create_user(**TEST_USER_CREDENTIALS)
    #     client.login(**TEST_USER_CREDENTIALS)
    #     response = client.get(url)
    #     response_np = np.load(io.BytesIO(response.content))
    #     assert response_np.shape[0] == len(images_oct)

    # def test_numpy_endpoint_authenticated_oct_series_images_corresond(self, client, django_user_model):
    #     series_oct, images_oct = create_oct_series()
    #     url = reverse("retina:image-numpy", args=[images_oct[0].id])
    #     django_user_model.objects.create_user(**TEST_USER_CREDENTIALS)
    #     client.login(**TEST_USER_CREDENTIALS)
    #     response = client.get(url)
    #
    #     request_np_images = [np.array(PILImage.open(x.image.path)) for x in images_oct]
    #     response_np = np.load(io.BytesIO(response.content))
    #     for np_image in response_np:
    #         image_in_array = False
    #         for np_request_image in request_np_images:
    #             if np.array_equal(np_image, np_request_image):
    #                 image_in_array = True
    #
    #         if not image_in_array:
    #             pytest.fail("request OCT images do not match response images")
    #             break
