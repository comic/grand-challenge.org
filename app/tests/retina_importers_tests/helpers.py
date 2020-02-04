import json
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.authtoken.models import Token

from grandchallenge.subdomains.utils import reverse
from tests.cases_tests import RESOURCE_PATH
from tests.factories import UserFactory


def get_retina_user_with_token(is_retina_user=True, **user_kwargs):
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
    Retrieve auth token that can be inserted into client request for
    authentication

    :param user:
        "staff" for staff user, "normal" for normal user, else AnonymousUser
    :param token:
        (optional) authentication token, `user` is not used if this is defined
    """
    if token is None:
        if user == "staff":
            _, token = get_retina_user_with_token(is_staff=True)
        elif user == "normal":
            _, token = get_retina_user_with_token()
        elif user == "import_user":
            user = get_user_model().objects.get(
                username=settings.RETINA_IMPORT_USER_NAME
            )
            token_obj = Token.objects.create(user=user)
            token = token_obj.key

    auth_header = {}
    if token:
        auth_header.update({"HTTP_AUTHORIZATION": "Token " + token})

    return auth_header


# helper functions
def create_test_images(mha=False):
    """
    Create image for testing purposes
    :return: file
    """
    files = {}
    if mha:
        types = ("mha",)
    else:
        types = ("mhd", "zraw")
    for file_type in types:
        files[file_type] = load_test_image(file_type)
    return files


def load_test_image(file_type):
    img = BytesIO()
    with open(RESOURCE_PATH / f"image10x10x10.{file_type}", "rb") as fh:
        img.name = fh.name
        img.write(fh.read())
    img.seek(0)
    return img


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
        print(f"Warning: No json file in {path_to_file}")
    return None


def create_upload_image_test_data(
    data_type="default", with_image=True, mha=False
):
    # create image
    files = create_test_images(mha=mha)
    if data_type == "kappa":
        data = read_json_file("upload_image_valid_data_kappa.json")
    elif data_type == "areds":
        data = read_json_file("upload_image_valid_data_areds.json")
    else:
        data = read_json_file("upload_image_valid_data.json")

    if with_image:
        # create request payload
        if mha:
            data.update({"image_mha": files["mha"]})
        else:
            data.update({"image_hd": files["mhd"], "image_raw": files["zraw"]})
    return data


def create_upload_image_invalid_test_data(data_type="default", mha=False):
    # create image
    files = create_test_images(mha=mha)
    if data_type == "kappa":
        data = read_json_file("upload_image_invalid_data_kappa.json")
    elif data_type == "areds":
        data = read_json_file("upload_image_invalid_data_areds.json")
    else:
        data = read_json_file("upload_image_invalid_data.json")
    # create request payload
    if mha:
        data.update({"image_mha": files["mha"]})
    else:
        data.update({"image_hd": files["mhd"], "image_raw": files["zraw"]})
    return data


def remove_test_image(response):
    # Remove uploaded test image from filesystem
    response_obj = json.loads(response.content)
    full_path_to_image = settings.APPS_DIR / Path(
        response_obj["image"]["image"][1:]
    )
    Path.unlink(full_path_to_image)


def get_response_status(client, reverse_name, data, user="anonymous"):
    auth_header = get_auth_token_header(user)
    url = reverse(reverse_name)
    response = client.post(url, data=data, **auth_header)
    return response.status_code
