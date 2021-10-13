import pytest
from rest_framework.exceptions import ValidationError

from grandchallenge.uploads.serializers import UserUploadCreateSerializer


@pytest.mark.parametrize(
    "filename",
    (
        "/ok.bat",
        "./ok.bat",
        "../ok.bat",
        "/../ok.bat",
        "../../ok.bat",
        "/../../ok.bat",
        "~/ok.bat",
    ),
)
def test_validate_filename_exceptions(filename):
    serializer = UserUploadCreateSerializer()

    with pytest.raises(ValidationError):
        serializer.validate_filename(filename)


@pytest.mark.parametrize(
    "filename", ("ok.bat", "ok..bat", ".ok.bat", "..ok.bat", "..ok..bat",),
)
def test_validate_filename(filename):
    serializer = UserUploadCreateSerializer()

    assert filename == serializer.validate_filename(filename)
