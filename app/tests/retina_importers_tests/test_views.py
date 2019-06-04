import pytest
import json

from rest_framework import status

from grandchallenge.subdomains.utils import reverse
from tests.cases_tests.factories import (
    ImageFactoryWithImageFile,
    ImageFactoryWithImageFile3D,
)
from tests.factories import ImageFactory
from .helpers import (
    create_upload_image_test_data,
    create_upload_image_invalid_test_data,
    read_json_file,
    get_response_status,
    get_auth_token_header,
    create_element_spacing_request,
)


@pytest.mark.django_db
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
    "endpoint_type,reverse_name,annotation_data",
    [
        ("upload_image_rsbmes", "retina:importers:upload-image", False),
        ("upload_image_kappa", "retina:importers:upload-image", False),
        ("upload_image_areds", "retina:importers:upload-image", False),
        (
            "upload_etdrs",
            "retina:importers:upload-etdrs-grid-annotation",
            True,
        ),
        (
            "upload_measurement",
            "retina:importers:upload-measurement_annotation",
            True,
        ),
        (
            "upload_boolean",
            "retina:importers:upload-boolean-classification-annotation",
            True,
        ),
        ("upload_polygon", "retina:importers:upload-polygon-annotation", True),
        (
            "upload_registration",
            "retina:importers:upload-image-registration-landmarks",
            True,
        ),
    ],
)
class TestCustomUploadEndpoints:
    def test_view(
        self,
        client,
        endpoint_type,
        reverse_name,
        annotation_data,
        user,
        status_valid,
        status_invalid,
        valid,
    ):
        if "upload_image" in endpoint_type:
            data_type = endpoint_type.lstrip("upload_image_")
            if valid:
                data = create_upload_image_test_data(data_type=data_type)
            else:
                data = create_upload_image_invalid_test_data(
                    data_type=data_type
                )
        else:
            valid_str = "valid" if valid else "invalid"
            data = read_json_file(f"{endpoint_type}_{valid_str}_data.json")

        response_status = get_response_status(
            client, reverse_name, data, user, annotation_data
        )
        if valid:
            assert response_status == status_valid
        else:
            assert response_status == status_invalid


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
        auth_header = get_auth_token_header(user)
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
        auth_header = get_auth_token_header(user)
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
class TestSetElementSpacingEndpointAuthentication:
    def test_authentication(self, client, user, expected_status, access):
        response = create_element_spacing_request(client, user=user)
        assert response.status_code == expected_status
        if access:
            data = response.json()
            assert data["success"]


@pytest.mark.django_db
class TestSetElementSpacingEndpointErrors:
    def test_non_existing_image_error(self, client):
        image = ImageFactoryWithImageFile()
        image_name = image.name
        image.delete()
        response = create_element_spacing_request(
            client, image_name=image_name
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        r = response.json()
        assert "errors" in r
        assert r["errors"] == "Image does not exist"

    def test_non_existing_imagefile_error(self, client):
        image = ImageFactory()
        response = create_element_spacing_request(
            client, image_name=image.name
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        r = response.json()
        assert "errors" in r
        assert r["errors"] == "ImageFile matching query does not exist."

    def test_multiple_images_error(self, client):
        image = ImageFactoryWithImageFile()
        ImageFactoryWithImageFile(name=image.name)
        response = create_element_spacing_request(
            client, image_name=image.name
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        r = response.json()
        assert "errors" in r
        assert r["errors"] == "Image identifiers returns multiple images."


@pytest.mark.django_db
class TestSetElementSpacingEndpoint:
    def test_spacing_changes(self, client):
        image = ImageFactoryWithImageFile()
        element_spacing = (1.5, 0.5)
        sitk_image = image.get_sitk_image()
        original_spacing = sitk_image.GetSpacing()
        assert element_spacing != original_spacing

        response = create_element_spacing_request(
            client, image_name=image.name, es=element_spacing
        )

        assert response.status_code == status.HTTP_200_OK
        r = response.json()
        assert r["success"]

        assert element_spacing == image.get_sitk_image().GetSpacing()

    def test_image_with_study(self, client):
        image = ImageFactoryWithImageFile()
        ImageFactoryWithImageFile(name=image.name)
        response = create_element_spacing_request(
            client, image_name=image.name, study=image.study
        )
        assert response.status_code == status.HTTP_200_OK
        r = response.json()
        assert r["success"]

    def test_spacing_changes_3d(self, client):
        image = ImageFactoryWithImageFile3D()
        element_spacing = (2.5, 1.5, 0.5)
        sitk_image = image.get_sitk_image()
        original_spacing = sitk_image.GetSpacing()
        assert element_spacing != original_spacing

        response = create_element_spacing_request(
            client, image_name=image.name, es=element_spacing, is_3d=True
        )

        assert response.status_code == status.HTTP_200_OK
        r = response.json()
        assert r["success"]

        assert element_spacing == image.get_sitk_image().GetSpacing()
