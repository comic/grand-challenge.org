import pytest

from grandchallenge.uploads.widgets import UserUploadSingleWidget


@pytest.mark.parametrize(
    "allowed_file_types,expected_value",
    (
        # See issue #3711
        (None, None),
        ([], []),
        (["foo"], ["foo"]),
    ),
)
def test_correct_allowed_file_types_passed(allowed_file_types, expected_value):
    widget = UserUploadSingleWidget(allowed_file_types=allowed_file_types)

    context = widget.get_context(name="foo", value="bar", attrs={"id": "foo"})

    assert context["widget"]["allowed_file_types"]["value"] == expected_value


def test_filetype_checking_disabled_by_default():
    # See issue #3711
    widget = UserUploadSingleWidget()

    context = widget.get_context(name="foo", value="bar", attrs={"id": "foo"})

    assert context["widget"]["allowed_file_types"]["value"] is None
