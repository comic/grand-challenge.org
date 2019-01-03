from io import BytesIO
from PIL import Image as PILImage
from pathlib import Path
import json
from django.conf import settings
from django.contrib.auth.models import Group
from rest_framework.authtoken.models import Token
from rest_framework import status
from django.contrib.auth import get_user_model
from tests.viewset_helpers import TEST_USER_CREDENTIALS
from tests.factories import UserFactory
from tests.retina_images_tests.factories import ImageFactory
from tests.studies_tests.factories import StudyFactory
from tests.patients_tests.factories import PatientFactory
from tests.archives_tests.factories import ArchiveFactory
from grandchallenge.studies.models import Study
from tests.cases_tests import RESOURCE_PATH
from grandchallenge.subdomains.urls import reverse


def get_user_with_token(is_retina_user=True, **user_kwargs):
    user = UserFactory(**user_kwargs)
    if is_retina_user:
        grader_group, group_created = Group.objects.get_or_create(
            name=settings.RETINA_GRADERS_GROUP_NAME
        )
        grader_group.user_set.add(user)

    token = Token.objects.create(user=user)
    return user, token.key


def get_auth_token_header(user, token=None):
    """
    Retrieve auth token that can be inserted into client request for authentication
    :param user: "staff" for staff user, "normal" for normal user, else AnonymousUser
    :param token: (optional) authentication token, `user` is not used if this is defined
    :return:
    """
    if token is None:
        if user == "staff":
            _, token = get_user_with_token(is_staff=True)
        elif user == "normal":
            _, token = get_user_with_token()

    auth_header = {}
    if token:
        auth_header.update({"HTTP_AUTHORIZATION": "Token " + token})

    return auth_header


# helper functions
def create_test_images():
    """
    Create image for testing purposes
    :return: file
    """
    files = {}
    for file_type in ("mhd", "zraw"):
        files[file_type] = BytesIO()
        fh = open(RESOURCE_PATH / "image5x6x7.{}".format(file_type), "rb")
        files[file_type].name = fh.name
        files[file_type].write(fh.read())
        fh.close()
        files[file_type].seek(0)

    return files


def read_json_file(path_to_file):
    path_to_file = (
        Path("/app/tests/retina_importers_tests/test_data") / path_to_file
    )
    print(path_to_file.absolute())
    try:
        file = open(path_to_file, "r")
        if file.mode == "r":
            file_contents = file.read()
            file_object = json.loads(file_contents)
            return file_object
        else:
            raise FileNotFoundError()
    except FileNotFoundError:
        print("Warning: No json file in {}".format(path_to_file))
    return None


def create_upload_image_test_data():
    # create image
    files = create_test_images()
    data = read_json_file("upload_image_valid_data.json")
    # create request payload
    data.update({"image_hd": files["mhd"], "image_raw": files["zraw"]})
    return data


def create_upload_image_invalid_test_data():
    # create image
    files = create_test_images()
    data = read_json_file("upload_image_invalid_data.json")
    # create request payload
    data.update({"image_hd": files["mhd"], "image_raw": files["zraw"]})
    return data


def remove_test_image(response):
    # Remove uploaded test image from filesystem
    response_obj = json.loads(response.content)
    full_path_to_image = settings.APPS_DIR / Path(
        response_obj["image"]["image"][1:]
    )
    Path.unlink(full_path_to_image)


def get_response_status(
    client, reverse_name, data, user="anonymous", annotation_data=None
):
    auth_header = get_auth_token_header(user)
    url = reverse(reverse_name)
    if annotation_data:
        # create objects that need to exist in database before request is made
        patient = PatientFactory(name=data.get("patient_identifier"))
        existing_models = {"studies": [], "series": [], "images": []}
        images = []
        for data_row in data.get("data"):
            if (
                data_row.get("study_identifier")
                not in existing_models["studies"]
            ):
                study = StudyFactory(
                    name=data_row.get("study_identifier"), patient=patient
                )
                existing_models["studies"].append(study.name)
            else:
                study = Study.objects.get(
                    name=data_row.get("study_identifier")
                )

            if (
                data_row.get("image_identifier")
                not in existing_models["images"]
            ):
                image = ImageFactory(
                    name=data_row.get("image_identifier"), study=study
                )
                existing_models["images"].append(image.name)
                images.append(image)
        archive = ArchiveFactory(
            name=data.get("archive_identifier"), images=images
        )

        response = client.post(
            url,
            data=json.dumps(data),
            content_type="application/json",
            **auth_header,
        )
    else:
        response = client.post(url, data=data, **auth_header)
    return response.status_code


def create_test_method(
    reverse_name, data, user, expected_status, annotation_data=None
):
    def test_method(self, client):
        response_status = get_response_status(
            client, reverse_name, data, user, annotation_data
        )
        assert response_status == expected_status

    return test_method


def batch_test_upload_views(batch_test_data, test_class):
    for name, test_data in batch_test_data.items():
        user_status_tuple = (
            (
                "anonymous",
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_401_UNAUTHORIZED,
            ),
            ("normal", status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN),
            ("staff", status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST),
        )
        for (
            user,
            expected_status_valid,
            expected_status_invalid,
        ) in user_status_tuple:
            for valid_data in (False, True):
                post_data = (
                    test_data["data"]
                    if valid_data
                    else test_data["invalid_data"]
                )
                test_method = create_test_method(
                    test_data["reverse_name"],
                    post_data,
                    user,
                    expected_status_valid
                    if valid_data
                    else expected_status_invalid,
                    annotation_data=test_data.get("annotation_data"),
                )
                test_method.__name__ = "test_{}_view_{}_{}_data".format(
                    name, user, "valid" if valid_data else "invalid"
                )
                setattr(test_class, test_method.__name__, test_method)
