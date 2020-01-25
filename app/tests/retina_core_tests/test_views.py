import io

import SimpleITK
import numpy as np
import pytest
from PIL import Image as PILImage
from django.conf import settings
from django.urls import reverse as django_reverse
from rest_framework import status

from grandchallenge.subdomains.utils import reverse
from tests.cases_tests.factories import ImageFactoryWithImageFile
from tests.retina_api_tests.helpers import client_login
from tests.retina_importers_tests.helpers import get_retina_user_with_token


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
        user, _ = get_retina_user_with_token()
        client.force_login(user=user)
        try:
            response = client.get(url)
            assert response.status_code == status.HTTP_200_OK
        except ValueError as e:
            assert "Missing staticfiles manifest entry for" in str(e)

    def test_auth_staff(self, client):
        url = reverse("retina:home")
        user, _ = get_retina_user_with_token()
        client.force_login(user=user)

        try:
            response = client.get(url)
            assert response.status_code == status.HTTP_200_OK
        except ValueError as e:
            # In CI a ValueError will be raised because django can't find all
            # static files since the static files are in a closed source
            # submodule (DIAGNijmegen/retina-frontend)
            assert "Missing staticfiles manifest entry for" in str(e)


@pytest.mark.django_db
class TestCustomImageViews:
    def test_thumbnail_endpoint_non_authenticated(self, client):
        image = ImageFactoryWithImageFile()
        url = reverse("retina:image-thumbnail", args=[image.id])
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_thumbnail_endpoint_authenticated_normal_non_auth(
        self, client, django_user_model
    ):
        image = ImageFactoryWithImageFile()
        url = reverse("retina:image-thumbnail", args=[image.id])
        # login client
        client, _ = client_login(client, user="normal")
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_thumbnail_endpoint_authenticated_non_existant(
        self, client, django_user_model
    ):
        image = ImageFactoryWithImageFile()
        url = reverse("retina:image-thumbnail", args=[image.id])
        # login client
        client, _ = client_login(client, user="retina_user")
        image.delete()  # remove model so response must return 404
        response = client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_thumbnail_endpoint_authenticated_no_perm(
        self, client, django_user_model
    ):
        image = ImageFactoryWithImageFile()
        url = reverse("retina:image-thumbnail", args=[image.id])
        client, _ = client_login(client, user="retina_user")
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_thumbnail_endpoint_authenticated(self, client, django_user_model):
        image = ImageFactoryWithImageFile()
        image.permit_viewing_by_retina_users()
        url = reverse("retina:image-thumbnail", args=[image.id])
        client, _ = client_login(client, user="retina_user")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-type"] == "image/png"

        response_np = np.array(
            PILImage.open(io.BytesIO(response.content)), np.uint8
        )
        sitk_image = image.get_sitk_image()
        depth = sitk_image.GetDepth()
        nda_image = SimpleITK.GetArrayFromImage(sitk_image)
        if depth > 0:
            nda_image = nda_image[depth // 2]
        expected_np = nda_image.astype(np.uint8)
        assert np.array_equal(response_np, expected_np)

    def test_numpy_endpoint_non_authenticated(self, client):
        image = ImageFactoryWithImageFile()
        url = reverse("retina:image-numpy", args=[image.id])
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_numpy_endpoint_normal_non_authenticated(self, client):
        image = ImageFactoryWithImageFile()
        url = reverse("retina:image-numpy", args=[image.id])
        client, _ = client_login(client, user="normal")
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_numpy_endpoint_authenticated_non_existant(
        self, client, django_user_model
    ):
        image = ImageFactoryWithImageFile()
        url = reverse("retina:image-numpy", args=[image.id])
        client, _ = client_login(client, user="retina_user")

        image.delete()  # remove model so response must return 404
        response = client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_numpy_endpoint_authenticated_status_no_perm(
        self, client, django_user_model
    ):
        image = ImageFactoryWithImageFile()
        url = reverse("retina:image-numpy", args=[image.id])
        client, _ = client_login(client, user="retina_user")
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_numpy_endpoint_authenticated_status(
        self, client, django_user_model
    ):
        image = ImageFactoryWithImageFile()
        image.permit_viewing_by_retina_users()
        url = reverse("retina:image-numpy", args=[image.id])
        client, _ = client_login(client, user="retina_user")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-type"] == "application/octet-stream"

    def test_numpy_endpoint_authenticated_images_correspond(
        self, client, django_user_model
    ):
        image = ImageFactoryWithImageFile(
            modality__modality=settings.MODALITY_CF
        )
        image.permit_viewing_by_retina_users()
        url = reverse("retina:image-numpy", args=[image.id])
        client, _ = client_login(client, user="retina_user")
        response = client.get(url)
        response_np = np.load(io.BytesIO(response.content))
        sitk_image = image.get_sitk_image()
        nda_image = SimpleITK.GetArrayFromImage(sitk_image)
        request_image_arr = nda_image.astype(np.int8)
        assert np.array_equal(response_np, request_image_arr)
