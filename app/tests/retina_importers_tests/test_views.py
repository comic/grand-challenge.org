import pytest

from rest_framework import status

from .helpers import (
    create_upload_image_test_data,
    create_upload_image_invalid_test_data,
    read_json_file,
    get_response_status,
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
        (
            "upload_polygon",
            "retina:importers:upload-polygon-annotation",
            True,
        ),
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
