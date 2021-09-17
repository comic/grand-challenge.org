import base64
import json
import random
from io import BytesIO

import SimpleITK
import pytest
from PIL import Image as PILImage
from django.conf import settings
from django.core.cache import cache
from knox.models import AuthToken
from rest_framework import status
from rest_framework.compat import LONG_SEPARATORS, SHORT_SEPARATORS
from rest_framework.settings import api_settings
from rest_framework.utils import encoders

from grandchallenge.cases.models import ImageFile
from grandchallenge.retina_api.serializers import (
    TreeImageSerializer,
    TreeObjectSerializer,
)
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
class TestArchiveAPIView:
    @staticmethod
    def perform_request(client, user, pk=None):
        url = reverse(
            "retina:api:archive-data-api-view",
            args=[pk] if pk is not None else [],
        )
        user_model = get_user_from_str(user)
        kwargs = {}
        if user_model is not None and not isinstance(user_model, str):
            _, token = AuthToken.objects.create(user=user_model)
            kwargs.update({"HTTP_AUTHORIZATION": f"Bearer {token}"})
        return client.get(url, **kwargs)

    @staticmethod
    def perform_request_as_user(client, user, pk=None):
        url = reverse(
            "retina:api:archive-data-api-view",
            args=[pk] if pk is not None else [],
        )
        kwargs = {}
        _, token = AuthToken.objects.create(user=user)
        kwargs.update({"HTTP_AUTHORIZATION": f"Bearer {token}"})
        return client.get(url, **kwargs)

    @staticmethod
    def expected_result_json(objects, images):
        objects_serialized = TreeObjectSerializer(objects, many=True).data
        images_serialized = TreeImageSerializer(images, many=True).data

        response = {
            "directories": sorted(objects_serialized, key=lambda x: x["name"]),
            "images": sorted(images_serialized, key=lambda x: x["name"]),
        }
        return json.dumps(
            response,
            cls=encoders.JSONEncoder,
            ensure_ascii=not api_settings.UNICODE_JSON,
            allow_nan=not api_settings.STRICT_JSON,
            separators=SHORT_SEPARATORS
            if api_settings.COMPACT_JSON
            else LONG_SEPARATORS,
        )

    @pytest.mark.parametrize(
        "user,expected_status",
        [
            ("anonymous", status.HTTP_401_UNAUTHORIZED),
            ("normal", status.HTTP_403_FORBIDDEN),
            ("staff", status.HTTP_403_FORBIDDEN),
            ("retina_user", status.HTTP_200_OK),
        ],
    )
    def test_access(self, client, user, expected_status):
        response = self.perform_request(client, user)
        assert response.status_code == expected_status

    def test_empty(self, client):
        # Clear cache manually
        cache.clear()
        response = self.perform_request(client, "retina_user")
        assert response.status_code == status.HTTP_200_OK
        assert response.content == b'{"directories":[],"images":[]}'

    @pytest.mark.parametrize(
        "permission", (True, False),
    )
    @pytest.mark.parametrize(
        "pk,objects,images",
        [
            # TODO reenable test after Archive permission filtering is implemented correctly
            # (None, ["archive1", "archive2"], None),
            ("archive1", ["patient11", "patient12"], None),
            ("patient11", ["study111", "study112", "study113"], None),
            ("study111", [], "images111"),
            ("archive2", [], "images211"),
        ],
    )
    def test_with_data(
        self,
        client,
        archive_patient_study_image_set,
        permission,
        pk,
        objects,
        images,
    ):
        # Clear cache manually
        cache.clear()
        user = get_user_from_str("retina_user")
        if permission:
            archive_patient_study_image_set.archive1.add_user(user)
            archive_patient_study_image_set.archive2.add_user(user)
        if pk is not None:
            pk = getattr(archive_patient_study_image_set, pk).pk
        response = self.perform_request_as_user(client, user, pk)
        if permission:
            assert response.status_code == status.HTTP_200_OK
            objects = [
                getattr(archive_patient_study_image_set, o) for o in objects
            ]
            imgs = []
            if images is not None:
                imgs = getattr(archive_patient_study_image_set, images)
            assert response.content.decode() == self.expected_result_json(
                objects, imgs
            )
        else:
            assert response.status_code == status.HTTP_200_OK
            assert response.content == b'{"directories":[],"images":[]}'

    def test_only_load_metaio_images(
        self, client, archive_patient_study_image_set
    ):
        cache.clear()
        user = get_user_from_str("retina_user")
        archive_patient_study_image_set.archive1.add_user(user)
        pk = archive_patient_study_image_set.study113.pk

        for (index, image) in enumerate(
            archive_patient_study_image_set.images111
        ):
            if index % 2 == 0:
                continue
            for image_file in image.files.all():
                image_file.image_type = ImageFile.IMAGE_TYPE_DZI
                image_file.save()

        response = self.perform_request_as_user(client, user, pk)
        assert response.status_code == status.HTTP_200_OK
        result = json.loads(response.content)
        assert len(result["images"]) == len(
            archive_patient_study_image_set.images113
        )
        res_img_ids = {i["id"] for i in result["images"]}
        exp_img_ids = {
            str(i.pk) for i in archive_patient_study_image_set.images113
        }
        assert res_img_ids == exp_img_ids

    def test_number_of_queries(
        self,
        client,
        archive_patient_study_image_set,
        django_assert_max_num_queries,
    ):
        cache.clear()
        user = get_user_from_str("retina_user")
        archive_patient_study_image_set.archive1.add_user(user)
        pk = archive_patient_study_image_set.study113.pk

        with django_assert_max_num_queries(22):
            self.perform_request_as_user(client, user, pk)


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
