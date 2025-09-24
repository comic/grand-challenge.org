import pytest

from grandchallenge.uploads.widgets import (
    DICOMUserUploadMultipleWidget,
    UserUploadSingleWidget,
)


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


def test_dicom_user_upload_multiple_widget_allows_multiple():
    widget = DICOMUserUploadMultipleWidget()
    context = widget.get_context(name="foo", value="bar", attrs={"id": "foo"})

    assert context["widget"]["attrs"].get("multiple") is True


def test_dicom_user_upload_media_includes_expected_js():
    widget = DICOMUserUploadMultipleWidget()

    for js_file in (
        "vendored/uppy/uppy.min.js",
        "js/user_upload.js",
        "vendored/dcmjs/build/dcmjs.min.js",
        "js/file_preprocessors.js",
    ):
        assert js_file in widget.media._js


def test_dicom_user_upload_multiple_widget_increased_max_number_of_files():
    widget = DICOMUserUploadMultipleWidget()
    context = widget.get_context(name="foo", value="bar", attrs={"id": "foo"})

    assert context["widget"]["attrs"].get("max_number_files") == 2000
