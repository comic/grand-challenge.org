import base64
import json
import random
from io import BytesIO

import SimpleITK
import pytest
from PIL import Image as PILImage
from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.compat import LONG_SEPARATORS, SHORT_SEPARATORS
from rest_framework.settings import api_settings
from rest_framework.utils import encoders

from grandchallenge.retina_api.serializers import (
    TreeImageSerializer,
    TreeObjectSerializer,
)
from grandchallenge.subdomains.utils import reverse
from tests.cases_tests.factories import (
    ImageFactoryWithImageFile,
    ImageFactoryWithImageFile2DLarge,
    ImageFactoryWithImageFile3DLarge3Slices,
    ImageFactoryWithImageFile3DLarge4Slices,
)
from tests.retina_api_tests.helpers import (
    batch_test_data_endpoints,
    batch_test_image_endpoint_redirects,
    client_force_login,
    client_login,
    create_datastructures_data,
    get_user_from_str,
)


@pytest.mark.django_db
class TestArchiveIndexAPIEndpoints:
    def test_archive_view_non_auth(self, client):
        # Clear cache manually (this is not done by pytest-django for some reason...)
        cache.clear()
        url = reverse("retina:api:archives-api-view")
        response = client.get(url, HTTP_ACCEPT="application/json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_archive_view_normal_non_auth(self, client):
        # Create data
        create_datastructures_data()

        # login client
        client, _ = client_login(client, user="normal")

        url = reverse("retina:api:archives-api-view")
        response = client.get(url, HTTP_ACCEPT="application/json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_archive_view_retina_auth(self, client):
        # Create data
        create_datastructures_data()

        # login client
        client, _ = client_login(client, user="retina_user")

        url = reverse("retina:api:archives-api-view")
        response = client.get(url, HTTP_ACCEPT="application/json")
        assert response.status_code == status.HTTP_200_OK

    def test_archive_view_returns_correct_data(self, client):
        # Clear cache manually (this is not done by pytest-django for some reason...)
        cache.clear()
        # Create data
        (
            datastructures,
            datastructures_aus,
            oct_obs_registration,
            oct_obs_registration_aus,
        ) = create_datastructures_data()

        # login client
        client, _ = client_login(client, user="retina_user")

        url = reverse("retina:api:archives-api-view")
        response = client.get(url, HTTP_ACCEPT="application/json")
        response_data = json.loads(response.content)
        # check if correct data is sent
        expected_response_data = {
            "subfolders": {
                datastructures["archive"].name: {
                    "subfolders": {
                        datastructures["patient"].name: {
                            "subfolders": {
                                datastructures["study_oct"].name: {
                                    "info": "level 5",
                                    "images": {
                                        datastructures["image_oct"].name: {
                                            "images": {
                                                "trc_000": "no info",
                                                "obs_000": str(
                                                    datastructures[
                                                        "image_obs"
                                                    ].id
                                                ),
                                                "mot_comp": "no info",
                                                "trc_001": "no info",
                                                "oct": str(
                                                    datastructures[
                                                        "image_oct"
                                                    ].id
                                                ),
                                            },
                                            "info": {
                                                "voxel_size": {
                                                    "axial": 0,
                                                    "lateral": 0,
                                                    "transversal": 0,
                                                },
                                                "date": datastructures[
                                                    "study_oct"
                                                ].datetime.strftime(
                                                    "%Y/%m/%d %H:%M:%S"
                                                ),
                                                "registration": {
                                                    "obs": "Checked separately",
                                                    "trc": [0, 0, 0, 0],
                                                },
                                            },
                                        }
                                    },
                                    "name": datastructures["study_oct"].name,
                                    "id": str(datastructures["study_oct"].id),
                                    "subfolders": {},
                                },
                                datastructures["study"].name: {
                                    "info": "level 5",
                                    "images": {
                                        datastructures["image_cf"].name: str(
                                            datastructures["image_cf"].id
                                        )
                                    },
                                    "name": datastructures["study"].name,
                                    "id": str(datastructures["study"].id),
                                    "subfolders": {},
                                },
                            },
                            "info": "level 4",
                            "name": datastructures["patient"].name,
                            "id": str(datastructures["patient"].id),
                            "images": {},
                        }
                    },
                    "info": "level 3",
                    "name": datastructures["archive"].name,
                    "id": str(datastructures["archive"].id),
                    "images": {},
                },
                datastructures_aus["archive"].name: {
                    "subfolders": {
                        datastructures_aus["patient"].name: {
                            "subfolders": {},
                            "info": "level 4",
                            "name": datastructures_aus["patient"].name,
                            "id": str(datastructures_aus["patient"].id),
                            "images": {
                                datastructures_aus["image_oct"].name: {
                                    "images": {
                                        "trc_000": "no info",
                                        "obs_000": str(
                                            datastructures_aus["image_obs"].id
                                        ),
                                        "mot_comp": "no info",
                                        "trc_001": "no info",
                                        "oct": str(
                                            datastructures_aus["image_oct"].id
                                        ),
                                    },
                                    "info": {
                                        "voxel_size": {
                                            "axial": 0,
                                            "lateral": 0,
                                            "transversal": 0,
                                        },
                                        "date": datastructures_aus[
                                            "study_oct"
                                        ].datetime.strftime(
                                            "%Y/%m/%d %H:%M:%S"
                                        ),
                                        "registration": {
                                            "obs": "Checked separately",
                                            "trc": [0, 0, 0, 0],
                                        },
                                    },
                                },
                                datastructures_aus["image_cf"].name: str(
                                    datastructures_aus["image_cf"].id
                                ),
                            },
                        }
                    },
                    "info": "level 3",
                    "name": datastructures_aus["archive"].name,
                    "id": str(datastructures_aus["archive"].id),
                    "images": {},
                },
            },
            "info": "level 2",
            "name": "Archives",
            "id": "none",
            "images": {},
        }

        # Compare floats separately because of intricacies of floating-point arithmetic in python
        try:
            # Get info objects of both archives in response data
            response_archive_info = (
                response_data.get("subfolders")
                .get(datastructures["archive"].name)
                .get("subfolders")
                .get(datastructures["patient"].name)
                .get("subfolders")
                .get(datastructures["study_oct"].name)
                .get("images")
                .get(datastructures["image_oct"].name)
                .get("info")
            )
            response_archive_australia_info = (
                response_data.get("subfolders")
                .get(datastructures_aus["archive"].name)
                .get("subfolders")
                .get(datastructures_aus["patient"].name)
                .get("images")
                .get(datastructures_aus["image_oct"].name)
                .get("info")
            )

            floats_to_compare = (
                []
            )  # list of (response_float, expected_float, name) tuples
            for archive, response_info, oor in (
                ("Rotterdam", response_archive_info, oct_obs_registration),
                (
                    "Australia",
                    response_archive_australia_info,
                    oct_obs_registration_aus,
                ),
            ):
                # oct obs registration
                response_obs = response_info.get("registration").get("obs")
                rv = oor.registration_values
                floats_to_compare.append(
                    (
                        response_obs[0],
                        rv[0][0],
                        archive + " obs oct registration top left x",
                    )
                )
                floats_to_compare.append(
                    (
                        response_obs[1],
                        rv[0][1],
                        archive + " obs oct registration top left y",
                    )
                )
                floats_to_compare.append(
                    (
                        response_obs[2],
                        rv[1][0],
                        archive + " obs oct registration bottom right x",
                    )
                )
                floats_to_compare.append(
                    (
                        response_obs[3],
                        rv[1][1],
                        archive + " obs oct registration bottom right y",
                    )
                )

            # Compare floats
            for result, expected, name in floats_to_compare:
                if result != pytest.approx(expected):
                    pytest.fail(name + " does not equal expected value")

            # Clear voxel and obs registration objects before response object to expected object comparison
            response_data["subfolders"][datastructures["archive"].name][
                "subfolders"
            ][datastructures["patient"].name]["subfolders"][
                datastructures["study_oct"].name
            ][
                "images"
            ][
                datastructures["image_oct"].name
            ][
                "info"
            ][
                "registration"
            ][
                "obs"
            ] = "Checked separately"

            response_data["subfolders"][datastructures_aus["archive"].name][
                "subfolders"
            ][datastructures_aus["patient"].name]["images"][
                datastructures_aus["image_oct"].name
            ][
                "info"
            ][
                "registration"
            ][
                "obs"
            ] = "Checked separately"

        except (AttributeError, KeyError, TypeError):
            pytest.fail("Response object structure is not correct")

        assert response_data == expected_response_data

    def test_caching(self, client):
        # Clear cache manually
        cache.clear()
        # Perform normal request
        datastructures, _, _, _ = create_datastructures_data()
        client, _ = client_login(client, user="retina_user")
        url = reverse("retina:api:archives-api-view")
        response = client.get(url, HTTP_ACCEPT="application/json")
        response_data = json.loads(response.content)
        # Remove archive and perform request again
        datastructures["archive"].delete()
        response = client.get(url, HTTP_ACCEPT="application/json")
        # Check that response is cached so it is not changed
        assert json.loads(response.content) == response_data


@pytest.mark.django_db
class TestImageAPIEndpoint:
    # test methods are added dynamically
    pass


batch_test_image_endpoint_redirects(TestImageAPIEndpoint)


@pytest.mark.django_db
class TestDataAPIEndpoint:
    # test methods are added dynamically
    pass


batch_test_data_endpoints(TestDataAPIEndpoint)


@pytest.mark.django_db
class TestImageElementSpacingView:
    @pytest.mark.parametrize(
        "user", ["anonymous", "normal", "staff", "retina_user"]
    )
    def test_no_access(self, client, user):
        image = ImageFactoryWithImageFile()
        url = reverse("retina:api:image-element-spacing-view", args=[image.pk])
        client, _ = client_login(client, user=user)
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize(
        "user,expected_status",
        [
            ("anonymous", status.HTTP_403_FORBIDDEN),
            ("normal", status.HTTP_403_FORBIDDEN),
            ("staff", status.HTTP_403_FORBIDDEN),
            ("retina_user", status.HTTP_200_OK),
        ],
    )
    def test_access(self, client, user, expected_status):
        image = ImageFactoryWithImageFile()
        image.permit_viewing_by_retina_users()
        url = reverse("retina:api:image-element-spacing-view", args=[image.pk])
        client, _ = client_login(client, user=user)
        response = client.get(url)
        assert response.status_code == expected_status

    def test_returns_correct_spacing(self, client):
        image = ImageFactoryWithImageFile()
        image.permit_viewing_by_retina_users()
        url = reverse("retina:api:image-element-spacing-view", args=[image.pk])
        client, _ = client_login(client, user="retina_user")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        r = response.json()
        assert list(image.get_sitk_image().GetSpacing()) == r


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
            token_object, _ = Token.objects.get_or_create(user=user_model)
            kwargs.update({"HTTP_AUTHORIZATION": f"Token {token_object.key}"})
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
        "pk,objects,images",
        [
            (None, ["archive1", "archive2"], None),
            ("archive1", ["patient11", "patient12"], None),
            ("patient11", ["study111", "study112", "study113"], None),
            ("study111", [], "images111"),
            ("archive2", [], "images211"),
        ],
    )
    def test_with_data_patient(
        self, client, archive_patient_study_image_set, pk, objects, images
    ):
        # Clear cache manually
        cache.clear()
        if pk is not None:
            pk = getattr(archive_patient_study_image_set, pk).pk
        response = self.perform_request(client, "retina_user", pk)
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

    def test_caching(self, client, archive_patient_study_image_set):
        # Clear cache manually
        cache.clear()
        # Perform normal request
        response = self.perform_request(client, "retina_user")
        assert response.status_code == status.HTTP_200_OK
        json_response = response.content.decode()
        # Remove data
        archive_patient_study_image_set.archive1.delete()
        archive_patient_study_image_set.archive2.delete()
        # Perform request again and expect unchanged response
        response = self.perform_request(client, "retina_user")
        assert response.status_code == status.HTTP_200_OK
        assert response.content.decode() == json_response


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
            token_object, _ = Token.objects.get_or_create(user=user_model)
            kwargs.update({"HTTP_AUTHORIZATION": f"Token {token_object.key}"})
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
        token = f"Token {Token.objects.create(user=user_model).key}"
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
            BytesIO(base64.b64decode(response.content))
        )
        assert response.content == image_base64_str
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
