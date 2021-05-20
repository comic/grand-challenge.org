import json
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from guardian.utils import get_anonymous_user
from knox.models import AuthToken

from tests.cases_tests import RESOURCE_PATH
from tests.factories import UserFactory


def get_retina_user_with_token(**user_kwargs):
    user = UserFactory(**user_kwargs)

    grader_group, group_created = Group.objects.get_or_create(
        name=settings.RETINA_GRADERS_GROUP_NAME
    )
    grader_group.user_set.add(user)

    _, token = AuthToken.objects.create(user=user)
    return user, token


def get_auth_token_header(username):
    """
    Retrieve auth token that can be inserted into client request for
    authentication

    :param user:
        "staff" for staff user, "normal" for normal user, else AnonymousUser
    """
    if username == "staff":
        user, token = get_retina_user_with_token(is_staff=True)
    elif username == "normal":
        user, token = get_retina_user_with_token()
    elif username == "import_user":
        user = get_user_model().objects.get(
            username=settings.RETINA_IMPORT_USER_NAME
        )
        _, token = AuthToken.objects.create(user=user)
    elif username == "anonymous":
        user = get_anonymous_user()
        token = None
    else:
        raise ValueError("User not defined")

    auth_header = {}
    if token:
        auth_header.update({"HTTP_AUTHORIZATION": f"Bearer {token}"})

    return user, auth_header


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
        file = open(path_to_file)
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
