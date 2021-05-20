import json

import pytest
from django.conf import settings
from rest_framework import status

from grandchallenge.subdomains.utils import reverse
from tests.archives_tests.factories import ArchiveFactory
from tests.cases_tests.factories import ImageFactoryWithImageFile
from tests.factories import ImagingModalityFactory
from tests.retina_importers_tests.helpers import (
    create_upload_image_invalid_test_data,
    create_upload_image_test_data,
    get_auth_token_header,
)


@pytest.mark.django_db
@pytest.mark.parametrize("mha", [True, False])
@pytest.mark.parametrize("valid", [True, False])
@pytest.mark.parametrize(
    "user,status_valid,status_invalid",
    [
        (
            "anonymous",
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_401_UNAUTHORIZED,
        ),
        ("normal", status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN),
        ("staff", status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN),
        ("import_user", status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST),
    ],
)
@pytest.mark.parametrize(
    "endpoint_type,reverse_name",
    [
        ("upload_image_rsbmes", "retina:importers:upload-image"),
        ("upload_image_kappa", "retina:importers:upload-image"),
        ("upload_image_areds", "retina:importers:upload-image"),
    ],
)
class TestCustomUploadEndpoints:
    def test_view(
        self,
        client,
        endpoint_type,
        reverse_name,
        user,
        status_valid,
        status_invalid,
        valid,
        mha,
    ):
        # Create necessary modalities and archives
        ImagingModalityFactory(modality=settings.MODALITY_CF)
        archives = [
            ArchiveFactory(title="Test archive"),
            ArchiveFactory(title="Test kappa archive"),
            ArchiveFactory(title="AREDS 2014"),
        ]

        user, auth_header = get_auth_token_header(user)

        for archive in archives:
            archive.add_uploader(user)

        data_type = endpoint_type.replace("upload_image_", "")
        if valid:
            data = create_upload_image_test_data(data_type=data_type, mha=mha)
        else:
            data = create_upload_image_invalid_test_data(
                data_type=data_type, mha=mha
            )

        url = reverse(reverse_name)
        response = client.post(url, data=data, **auth_header)

        if valid:
            assert response.status_code == status_valid
        else:
            assert response.status_code == status_invalid


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user,expected_status, access",
    [
        ("anonymous", status.HTTP_401_UNAUTHORIZED, False),
        ("normal", status.HTTP_403_FORBIDDEN, False),
        ("staff", status.HTTP_403_FORBIDDEN, False),
        ("import_user", status.HTTP_200_OK, True),
    ],
)
class TestCheckImageEndpoint:
    def test_non_existing_image(self, client, user, expected_status, access):
        _, auth_header = get_auth_token_header(user)
        url = reverse("retina:importers:check-image")

        data = json.dumps(create_upload_image_test_data(with_image=False))

        response = client.post(
            url, data=data, content_type="application/json", **auth_header
        )

        assert response.status_code == expected_status
        if access:
            data = response.json()
            assert not data["exists"]

    def test_existing_image(self, client, user, expected_status, access):
        _, auth_header = get_auth_token_header(user)
        url = reverse("retina:importers:check-image")

        image = ImageFactoryWithImageFile()
        data = json.dumps(
            {
                "patient_identifier": image.study.patient.name,
                "study_identifier": image.study.name,
                "image_eye_choice": image.eye_choice,
                "image_stereoscopic_choice": image.stereoscopic_choice,
                "image_field_of_view": image.field_of_view,
                "image_identifier": image.name,
                "image_modality": image.modality.modality,
            }
        )

        r = client.post(
            url, data=data, content_type="application/json", **auth_header
        )

        assert r.status_code == expected_status
        if access:
            response = r.json()
            assert response["exists"]
