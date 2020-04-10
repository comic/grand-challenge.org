import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.cache import cache

from grandchallenge.retina_api.models import ArchiveDataModel
from grandchallenge.retina_api.tasks import cache_archive_data
from tests.factories import UserFactory
from tests.retina_api_tests.helpers import create_datastructures_data


@pytest.mark.django_db
@pytest.mark.parametrize("permission", [False, True])
class TestCacheArchiveDataTasks:
    def test_caching(self, permission):
        cache.clear()
        # Create data
        user = UserFactory()
        retina_group = Group.objects.get(
            name=settings.RETINA_GRADERS_GROUP_NAME
        )
        retina_group.user_set.add(user)
        (
            datastructures,
            datastructures_aus,
            oct_obs_registration,
            oct_obs_registration_aus,
        ) = create_datastructures_data(archive_pars={"title": "RS1"})

        if permission:
            datastructures["archive"].add_user(user)
            datastructures_aus["archive"].add_user(user)

        # Run task synchronously
        cache_archive_data()

        # Check cached data
        archive_data_object, _ = ArchiveDataModel.objects.get_or_create(pk=1)
        archive_data = archive_data_object.value

        if not permission:
            expected_archive_data = {
                "id": "none",
                "images": {},
                "info": "level 2",
                "name": "Archives",
                "subfolders": {},
            }
            assert archive_data == expected_archive_data
            return

        expected_archive_data = {
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
                archive_data.get("subfolders")
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
                archive_data.get("subfolders")
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
            archive_data["subfolders"][datastructures["archive"].name][
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

            archive_data["subfolders"][datastructures_aus["archive"].name][
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

        assert archive_data == expected_archive_data
