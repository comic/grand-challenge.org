import pytest

from grandchallenge.core.utils import strtobool


@pytest.mark.parametrize(
    "val, result",
    [
        ("y", True),
        ("Y", True),
        ("yes", True),
        ("Yes", True),
        ("true", True),
        ("True", True),
        ("t", True),
        ("T", True),
        ("on", True),
        ("On", True),
        ("1", True),
        ("n", False),
        ("N", False),
        ("no", False),
        ("No", False),
        ("false", False),
        ("False", False),
        ("f", False),
        ("F", False),
        ("off", False),
        ("Off", False),
        ("0", False),
    ],
)
def test_strtobool(val, result):
    assert strtobool(val) is result


def test_strtobool_exception():
    with pytest.raises(ValueError):
        strtobool("foobar")
