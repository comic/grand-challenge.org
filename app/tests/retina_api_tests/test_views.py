import json
import pytest

from rest_framework import status
from django.core.cache import cache

from grandchallenge.subdomains.utils import reverse
from tests.retina_api_tests.helpers import (
    create_datastructures_data,
    batch_test_image_endpoint_redirects,
    batch_test_data_endpoints,
    client_login,
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
        datastructures, datastructures_aus, oct_obs_registration, oct_obs_registration_aus = (
            create_datastructures_data()
        )

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

            floats_to_compare = []  # list of (response_float, expected_float, name) tuples
            for archive, response_info, ds, oor in (
                (
                    "Rotterdam",
                    response_archive_info,
                    datastructures,
                    oct_obs_registration,
                ),
                (
                    "Australia",
                    response_archive_australia_info,
                    datastructures_aus,
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
