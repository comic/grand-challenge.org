import os
import shutil
import subprocess
import tempfile
import zipfile
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

TEST_RESOURCES = Path(__file__).parent / "resources"

DEFAULT_PHASE_CONTEXT_STUB = {
    "challenge": {
        "slug": "challenge-slug",
        "url": "https://challenge-slug.grand-challenge.org/",
    },
    "slug": "phase-slug",
    "archive": {
        "slug": "archive-slug",
        "url": "https://grand-challenge.org/archives/archive-slug/",
    },
    "algorithm_interfaces": [
        {
            "inputs": [
                {
                    "slug": "input-socket-slug",
                    "relative_path": "images/input-value",
                    "is_image_kind": True,
                    "is_panimg_kind": True,
                },
                {
                    "slug": "another-input-socket-slug",
                    "relative_path": "another-input-value.json",
                    "example_value": {"key": "value"},
                    "is_file_kind": True,
                    "is_json_kind": True,
                },
                {
                    "slug": "yet-another-input-socket-slug",
                    "relative_path": "yet-another-input-value.json",
                    "example_value": {"key": "value"},
                    "is_file_kind": True,
                    "is_json_kind": True,
                },
                {
                    "slug": "yet-another-non-json-input-socket-slug",
                    "relative_path": "yet-another-non-json-input-value",
                    "is_file_kind": True,
                },
                {
                    "slug": "json-file-input-socket-slug",
                    "relative_path": "json-file-input-value.json",
                    "example_value": {"key": "value"},
                    "is_json_kind": True,
                    "is_json_file_kind": True,
                },
                {
                    "slug": "dicom-image-set-input-socket-slug",
                    "relative_path": "images/dicom-image-set-input-value",
                    "is_dicom_image_kind": True,
                    "is_image_kind": True,
                },
            ],
            "outputs": [
                {
                    "slug": "output-socket-slug",
                    "relative_path": "images/output-value",
                    "is_image_kind": True,
                    "is_panimg_kind": True,
                },
                {
                    "slug": "another-output-socket-slug",
                    "relative_path": "output-value.json",
                    "example_value": {"key": "value"},
                    "is_file_kind": True,
                    "is_json_kind": True,
                },
                {
                    "slug": "yet-another-output-socket-slug",
                    "relative_path": "yet-another-output-value.json",
                    "example_value": {"key": "value"},
                    "is_file_kind": True,
                    "is_json_kind": True,
                },
                {
                    "slug": "yet-another-non-json-output-socket-slug",
                    "relative_path": "yet-another-non-json-output-value",
                    "is_file_kind": True,
                },
                {
                    "slug": "json-file-output-socket-slug",
                    "relative_path": "json-file-output-value.json",
                    "example_value": {"key": "value"},
                    "is_json_kind": True,
                    "is_json_file_kind": True,
                },
                {
                    "slug": "dicom-image-set-output-socket-slug",
                    "relative_path": "images/dicom-image-set-output-value",
                    "is_dicom_image_kind": True,
                    "is_image_kind": True,
                },
            ],
        },
        {
            "inputs": [
                {
                    "slug": "input-socket-slug-interface-2",
                    "relative_path": "images/input-value",
                    "is_image_kind": True,
                    "is_panimg_kind": True,
                }
            ],
            "outputs": [
                {
                    "slug": "output-socket-slug-interface-2",
                    "relative_path": "images/output-value",
                    "is_image_kind": True,
                    "is_panimg_kind": True,
                }
            ],
        },
    ],
    "evaluation_additional_inputs": [
        {
            "slug": "additional-input-socket-slug",
            "relative_path": "images/input-value",
            "is_image_kind": True,
            "is_panimg_kind": True,
        },
        {
            "slug": "additional-another-input-socket-slug",
            "relative_path": "another-input-value.json",
            "example_value": {"key": "value"},
            "is_json_kind": True,
            "is_file_kind": True,
        },
        {
            "slug": "additional-yet-another-input-socket-slug",
            "relative_path": "yet-another-input-value.json",
            "example_value": {"key": "value"},
            "is_file_kind": True,
            "is_json_kind": True,
        },
        {
            "slug": "additional-yet-another-non-json-input-socket-slug",
            "relative_path": "yet-another-non-json-input-value",
            "is_file_kind": True,
        },
        {
            "slug": "dicom-image-set-additional-input-socket-slug",
            "relative_path": "images/dicom-image-set-additional-input-socket-slug",
            "is_dicom_image_kind": True,
            "is_image_kind": True,
        },
    ],
    "evaluation_additional_outputs": [
        {
            "slug": "additional-output-socket-slug",
            "relative_path": "images/output-value",
            "is_image_kind": True,
            "is_panimg_kind": True,
        },
        {
            "slug": "additional-another-output-socket-slug",
            "relative_path": "output-value.json",
            "example_value": {"key": "value"},
            "is_file_kind": True,
            "is_json_kind": True,
        },
        {
            "slug": "additional-yet-another-output-socket-slug",
            "relative_path": "yet-another-output-value.json",
            "example_value": {"key": "value"},
            "is_json_kind": True,
            "is_file_kind": True,
        },
        {
            "slug": "additional-yet-another-non-json-output-socket-slug",
            "relative_path": "yet-another-non-json-output-value",
            "is_file_kind": True,
        },
        {
            "slug": "dicom-image-set-output-socket-slug",
            "relative_path": "images/dicom-image-set-output-value",
            "is_dicom_image_kind": True,
            "is_image_kind": True,
        },
    ],
}


DEFAULT_ALGORITHM_CONTEXT_STUB = {
    "title": "An algorithm",
    "slug": "an-algorithm",
    "url": "https://grand-challenge.org/algorithms/an-algorithm/",
    "algorithm_interfaces": [
        {
            "inputs": [
                {
                    "slug": "input-socket-slug",
                    "relative_path": "images/input-value",
                    "is_image_kind": True,
                    "is_panimg_kind": True,
                },
                {
                    "slug": "another-input-socket-slug",
                    "relative_path": "another-input-value.json",
                    "example_value": {"key": "value"},
                    "is_file_kind": True,
                    "is_json_kind": True,
                },
                {
                    "slug": "yet-another-input-socket-slug",
                    "relative_path": "yet-another-input-value.json",
                    "example_value": {"key": "value"},
                    "is_file_kind": True,
                    "is_json_kind": True,
                },
                {
                    "slug": "yet-another-non-json-input-socket-slug",
                    "relative_path": "yet-another-non-json-input-value",
                    "is_file_kind": True,
                },
                {
                    "slug": "json-file-input-socket-slug",
                    "relative_path": "json-file-input-value.json",
                    "example_value": {"key": "value"},
                    "is_json_kind": True,
                    "is_json_file_kind": True,
                },
                {
                    "slug": "dicom-image-set-input-socket-slug",
                    "relative_path": "images/dicom-image-set-input-value",
                    "is_dicom_image_kind": True,
                    "is_image_kind": True,
                },
            ],
            "outputs": [
                {
                    "slug": "output-socket-slug",
                    "relative_path": "images/output-value",
                    "is_image_kind": True,
                    "is_panimg_kind": True,
                },
                {
                    "slug": "another-output-socket-slug",
                    "relative_path": "output-value.json",
                    "example_value": {"key": "value"},
                    "is_file_kind": True,
                    "is_json_kind": True,
                },
                {
                    "slug": "yet-another-output-socket-slug",
                    "relative_path": "yet-another-output-value.json",
                    "example_value": {"key": "value"},
                    "is_file_kind": True,
                    "is_json_kind": True,
                },
                {
                    "slug": "yet-another-non-json-output-socket-slug",
                    "relative_path": "yet-another-non-json-output-value",
                    "is_file_kind": True,
                },
                {
                    "slug": "json-file-output-socket-slug",
                    "relative_path": "json-file-output-value.json",
                    "example_value": {"key": "value"},
                    "is_json_kind": True,
                    "is_json_file_kind": True,
                },
                {
                    "slug": "dicom-image-set-output-socket-slug",
                    "relative_path": "images/dicom-image-set-output-value",
                    "is_dicom_image_kind": True,
                    "is_image_kind": True,
                },
            ],
        },
        {
            "inputs": [
                {
                    "slug": "input-socket-slug-interface-2",
                    "relative_path": "images/input-value",
                    "is_image_kind": True,
                    "is_panimg_kind": True,
                }
            ],
            "outputs": [
                {
                    "slug": "output-socket-slug-interface-2",
                    "relative_path": "images/output-value",
                    "is_image_kind": True,
                    "is_panimg_kind": True,
                }
            ],
        },
    ],
}


unique_slugs_suffix = Counter()


def make_slugs_unique(d):
    """Ensure all slugs in the structure to make them unique"""
    global unique_slugs_suffix

    if isinstance(d, dict):
        if "slug" in d:
            original_slug = d["slug"]
            suffix = unique_slugs_suffix[original_slug]
            d["slug"] = f"{original_slug}-{suffix}"
            unique_slugs_suffix.update([original_slug])
        for item in d.values():
            make_slugs_unique(item)
    elif isinstance(d, list):
        for item in d:
            make_slugs_unique(item)
    return d


def add_numerical_slugs(d):
    """Add '00-' prefix to all slugs in the structure."""
    if isinstance(d, dict):
        if "slug" in d and not d["slug"].startswith("00-"):
            d["slug"] = f"00-{d['slug']}"
        for item in d.values():
            add_numerical_slugs(item)
    elif isinstance(d, list):
        for item in d:
            add_numerical_slugs(item)
    return d


def phase_context_factory(**kwargs):
    result = deepcopy(DEFAULT_PHASE_CONTEXT_STUB)
    result.update(kwargs)
    return make_slugs_unique(result)


def algorithm_template_context_factory(**kwargs):
    result = deepcopy(DEFAULT_ALGORITHM_CONTEXT_STUB)
    result.update(kwargs)
    return make_slugs_unique(result)


def _test_script_run(
    *,
    script_path,
    extra_arg=None,
):
    """Test a subprocess execution.

    Args
    ----
        script_path: The path to the script to execute
        extra_arg: Optional additional argument to pass to the script

    """
    command = [script_path]
    if extra_arg:
        command.append(extra_arg)

    result = subprocess.run(command, capture_output=True)
    if result.stderr or result.returncode != 0:  # Stderr should not be empty
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=command,
            stderr=result.stderr,
            output=result.stdout,
        )


@contextmanager
def mocked_binaries():
    """Mock the binaries in the PATH to avoid computationally intensive operations during testing."""
    mocks_bin = TEST_RESOURCES / "mocks" / "bin"
    current_path = os.environ.get("PATH", "")
    extended_path = f"{mocks_bin}:{current_path}"

    with patch.dict("os.environ", PATH=extended_path):
        yield


@contextmanager
def zipfile_to_filesystem(output_path, preserve_permissions=True):
    """
    Context manager that provides an in-memory zip file handle and optionally
    extracts its contents.

    Args
    ----
        output_dir (str, Path): Directory to extract the zip contents to
        after completion.

    Yields
    ------
        ZipFile: A ZipFile object that can be written to.
    """
    zip_handle = BytesIO()

    with zipfile.ZipFile(zip_handle, "w") as zip_file:
        yield zip_file

    # Extract contents to disk if output_dir is specified

    zip_handle.seek(0)
    os.makedirs(output_path, exist_ok=True)

    temp_zip = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    try:
        temp_zip.write(zip_handle.getvalue())
        temp_zip.close()

        if preserve_permissions:
            # Use a subprocess because the ZipFile.extractall does
            # not keep permissions: https://github.com/python/cpython/issues/59999
            subprocess.run(
                [
                    "unzip",
                    "-o",
                    temp_zip.name,
                    "-d",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
            )
        else:
            shutil.unpack_archive(temp_zip.name, output_path)
    finally:
        os.remove(temp_zip.name)
