import pytest
from django.core.exceptions import ValidationError

from grandchallenge.components.validators import validate_safe_path


@pytest.mark.parametrize(
    "rel_path",
    ["bar/../foo", "./foo", "../bar", "/sfdadfs", "////sfda", "foo/"],
)
def test_invalid_paths(rel_path):
    with pytest.raises(ValidationError):
        validate_safe_path(rel_path)


@pytest.mark.parametrize(
    "rel_path", ["foo", "foo/bar", "foo/bar.tar.gz", "foo/{{ filename }}.zip"]
)
def test_valid_paths(rel_path):
    validate_safe_path(rel_path)
