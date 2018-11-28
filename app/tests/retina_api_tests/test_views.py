import json
from rest_framework.test import APIRequestFactory
import pytest
from rest_framework import status
from django.urls import reverse
from django.core.cache import cache
from django.contrib.auth import get_user_model
from tests.viewset_helpers import TEST_USER_CREDENTIALS
from grandchallenge.retina_images.models import RetinaImage
from tests.datastructures_tests.factories import (
    ArchiveFactory,
    PatientFactory,
    StudyFactory,
    RetinaImageFactory,
    create_oct_series,
    create_some_datastructure_data,
)
from tests.registrations_tests.factories import OctObsRegistrationFactory
from tests.retina_api_tests.helpers import (
    create_datastructures_data,
    login_user_to_client,
    batch_test_image_endpoint_redirects,
    batch_test_data_endpoints,
)


@pytest.mark.django_db
class TestArchiveIndexAPIEndpoints:
    def test_archive_view_non_auth(self, client):
        url = reverse("archives-list")
        client = login_user_to_client(client)
        response = client.get(url)
        assert status.HTTP_403_FORBIDDEN == response.status_code

    def test_archive_view_auth(self, client):
        # Create data
        create_datastructures_data()

        # login user
        client = login_user_to_client(client, "normal")

        url = reverse("archives-list")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_archive_view_returns_correct_data(self, client):
        # Clear cache manually (this is not done by pytest-django for some reason...)
        cache.clear()
        # Create data
        datastructures, datastructures_aus, oct_obs_registration, oct_obs_registration_aus = (
            create_datastructures_data()
        )
        # login user
        client = login_user_to_client(client, "normal")

        url = reverse("archives-list")
        response = client.get(url)
        response_data = json.loads(response.content)
        # check if correct data is sent
        expected_response_data = {
            "subfolders": {
                datastructures["archive"].name: {
                    "subfolders": {
                        datastructures["patient"].name: {
                            "subfolders": {
                                datastructures["study"].name: {
                                    "info": "level 5",
                                    "images": {
                                        datastructures["image_cf"].name: "no tags"
                                    },
                                    "name": datastructures["study"].name,
                                    "id": str(datastructures["study"].id),
                                    "subfolders": {},
                                },
                                datastructures["study_oct"].name: {
                                    "info": "level 5",
                                    "images": {
                                        datastructures["oct_slices"][0].name: {
                                            "images": {
                                                "trc_000": "no info",
                                                "obs_000": "no info",
                                                "mot_comp": "no info",
                                                "trc_001": "no info",
                                                "oct": "no info",
                                            },
                                            "info": {
                                                "voxel_size": "Checked separately",
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
                                datastructures_aus["image_cf"].name: "no tags",
                                datastructures_aus["oct_slices"][0].name: {
                                    "images": {
                                        "trc_000": "no info",
                                        "obs_000": "no info",
                                        "mot_comp": "no info",
                                        "trc_001": "no info",
                                        "oct": "no info",
                                    },
                                    "info": {
                                        "voxel_size": "Checked separately",
                                        "date": datastructures_aus[
                                            "study_oct"
                                        ].datetime.strftime("%Y/%m/%d %H:%M:%S"),
                                        "registration": {
                                            "obs": "Checked separately",
                                            "trc": [0, 0, 0, 0],
                                        },
                                    },
                                },
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
            "name": "GA Archive",
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
                .get(datastructures["oct_slices"][0].name)
                .get("info")
            )
            response_archive_australia_info = (
                response_data.get("subfolders")
                .get(datastructures_aus["archive"].name)
                .get("subfolders")
                .get(datastructures_aus["patient"].name)
                .get("images")
                .get(datastructures_aus["oct_slices"][0].name)
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
                # voxel size
                response_voxel_size = response_info.get("voxel_size")
                floats_to_compare.append(
                    (
                        response_voxel_size["axial"],
                        ds["oct_slices"][0].voxel_size[0],
                        archive + " voxel size axial",
                    )
                )
                floats_to_compare.append(
                    (
                        response_voxel_size["lateral"],
                        ds["oct_slices"][0].voxel_size[1],
                        archive + " voxel size lateral",
                    )
                )
                floats_to_compare.append(
                    (
                        response_voxel_size["transversal"],
                        ds["oct_slices"][0].voxel_size[2],
                        archive + " voxel size transversal",
                    )
                )

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
            response_data["subfolders"][datastructures["archive"].name]["subfolders"][
                datastructures["patient"].name
            ]["subfolders"][datastructures["study_oct"].name]["images"][
                datastructures["oct_slices"][0].name
            ][
                "info"
            ][
                "voxel_size"
            ] = "Checked separately"

            response_data["subfolders"][datastructures["archive"].name]["subfolders"][
                datastructures["patient"].name
            ]["subfolders"][datastructures["study_oct"].name]["images"][
                datastructures["oct_slices"][0].name
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
                datastructures_aus["oct_slices"][0].name
            ][
                "info"
            ][
                "voxel_size"
            ] = "Checked separately"

            response_data["subfolders"][datastructures_aus["archive"].name][
                "subfolders"
            ][datastructures_aus["patient"].name]["images"][
                datastructures_aus["oct_slices"][0].name
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
