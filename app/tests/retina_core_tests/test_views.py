import io

import SimpleITK
import numpy as np
import pytest
from PIL import Image as PILImage
from rest_framework import status

from grandchallenge.subdomains.utils import reverse
from tests.cases_tests.factories import ImageFactoryWithImageFile
from tests.retina_api_tests.helpers import client_login


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
