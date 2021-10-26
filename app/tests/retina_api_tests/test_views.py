import base64
import random
from io import BytesIO

import SimpleITK
import pytest
from PIL import Image as PILImage
from django.conf import settings
from knox.models import AuthToken
from rest_framework import status

from grandchallenge.subdomains.utils import reverse
from tests.cases_tests.factories import (
    ImageFactoryWithImageFile,
    ImageFactoryWithImageFile16Bit,
    ImageFactoryWithImageFile2DLarge,
    ImageFactoryWithImageFile3DLarge3Slices,
    ImageFactoryWithImageFile3DLarge4Slices,
)
from tests.retina_api_tests.helpers import (
    client_force_login,
    get_user_from_str,
)


@pytest.mark.django_db
class TestBase64ThumbnailView:
    @pytest.mark.parametrize(
        "user,expected_status",
        [
            ("anonymous", status.HTTP_401_UNAUTHORIZED),
            ("normal", status.HTTP_403_FORBIDDEN),
            ("staff", status.HTTP_403_FORBIDDEN),
            ("retina_user", status.HTTP_200_OK),
        ],
    )
    def test_access_and_defaults(self, client, user, expected_status):
        image = ImageFactoryWithImageFile()
        image.permit_viewing_by_retina_users()
        url = reverse("retina:api:image-thumbnail", kwargs={"pk": image.pk})
        user_model = get_user_from_str(user)
        kwargs = {}
        if user_model is not None and not isinstance(user_model, str):
            _, token = AuthToken.objects.create(user=user_model)
            kwargs.update({"HTTP_AUTHORIZATION": f"Bearer {token}"})
        response = client.get(url, **kwargs)
        assert response.status_code == expected_status

    @staticmethod
    def perform_thumbnail_request(client, image, max_dimension):
        image.permit_viewing_by_retina_users()
        kwargs = {"pk": image.id}
        if max_dimension != settings.RETINA_DEFAULT_THUMBNAIL_SIZE:
            kwargs.update({"width": max_dimension, "height": max_dimension})
        url = reverse("retina:api:image-thumbnail", kwargs=kwargs)
        client, user_model = client_force_login(client, user="retina_user")
        _, token = AuthToken.objects.create(user=user_model)
        token = f"Bearer {token}"
        response = client.get(url, HTTP_AUTHORIZATION=token)
        return response

    @staticmethod
    def get_b64_from_image(image, max_dimension, is_3d=False):
        image_sitk = image.get_sitk_image()
        image_nparray = SimpleITK.GetArrayFromImage(image_sitk)
        if is_3d:
            depth = image_sitk.GetDepth()
            assert depth > 0
            # Get center slice of 3D image
            image_nparray = image_nparray[depth // 2]

        image_pil = PILImage.fromarray(image_nparray)
        image_pil.thumbnail((max_dimension, max_dimension), PILImage.ANTIALIAS)
        buffer = BytesIO()
        image_pil.save(buffer, format="png")
        image_base64_str = base64.b64encode(buffer.getvalue())
        return image_base64_str

    def do_test_thumbnail_creation(
        self, client, max_dimension, image, is_3d=False
    ):
        response = self.perform_thumbnail_request(client, image, max_dimension)

        assert response.status_code == status.HTTP_200_OK
        image_base64_str = self.get_b64_from_image(image, max_dimension, is_3d)

        returned_img = PILImage.open(
            BytesIO(base64.b64decode(response.json()["content"]))
        )
        assert response.json()["content"] == image_base64_str.decode()
        width, height = returned_img.size
        assert max(width, height) == max_dimension

    @pytest.mark.parametrize(
        "is_3d,image_factory",
        [
            (False, ImageFactoryWithImageFile2DLarge),
            (True, ImageFactoryWithImageFile3DLarge3Slices),
            (True, ImageFactoryWithImageFile3DLarge4Slices),
        ],
    )
    @pytest.mark.parametrize("max_dimension", ["default", "random"])
    def test_correct_image(self, client, max_dimension, is_3d, image_factory):
        image = image_factory()
        if max_dimension == "random":
            max_dimension = random.randint(1, 255)
        else:
            max_dimension = settings.RETINA_DEFAULT_THUMBNAIL_SIZE
        self.do_test_thumbnail_creation(
            client, max_dimension, image, is_3d=is_3d
        )

    def test_16bit_image(self, client):
        image = ImageFactoryWithImageFile16Bit()
        self.do_test_thumbnail_creation(
            client,
            max_dimension=settings.RETINA_DEFAULT_THUMBNAIL_SIZE,
            image=image,
            is_3d=True,
        )
