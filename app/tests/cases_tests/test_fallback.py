import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from panimg.image_builders.fallback import (
    format_error,
    image_builder_fallback,
)
from panimg.models import ColorSpace
from panimg.panimg import _build_files

from tests.cases_tests import RESOURCE_PATH


@pytest.mark.parametrize(
    "src,colorspace",
    (
        (RESOURCE_PATH / "test_grayscale.jpg", ColorSpace.GRAY),
        (RESOURCE_PATH / "test_rgb.jpg", ColorSpace.RGB),
        (RESOURCE_PATH / "test_grayscale.png", ColorSpace.GRAY),
        (RESOURCE_PATH / "test_rgb.png", ColorSpace.RGB),
        (RESOURCE_PATH / "test_rgba.png", ColorSpace.RGBA),
    ),
)
def test_image_builder_fallback(tmpdir, src, colorspace):
    dest = Path(tmpdir) / src.name
    shutil.copy(str(src), str(dest))
    files = {Path(d[0]).joinpath(f) for d in os.walk(tmpdir) for f in d[2]}
    with TemporaryDirectory() as output:
        result = _build_files(
            builder=image_builder_fallback,
            files=files,
            output_directory=output,
        )
    assert result.consumed_files == {dest}
    assert len(result.new_images) == 1
    image = result.new_images.pop()
    assert image.color_space == colorspace
    assert image.voxel_width_mm is None
    assert image.voxel_height_mm is None
    assert image.voxel_depth_mm is None


def test_image_builder_fallback_corrupt_file(tmpdir):
    src = RESOURCE_PATH / "corrupt.png"
    dest = Path(tmpdir) / src.name
    shutil.copy(str(src), str(dest))

    files = {Path(d[0]).joinpath(f) for d in os.walk(tmpdir) for f in d[2]}
    with TemporaryDirectory() as output:
        result = _build_files(
            builder=image_builder_fallback,
            files=files,
            output_directory=output,
        )

    assert result.file_errors == {
        dest: [format_error("Not a valid image file")],
    }
    assert result.consumed_files == set()
