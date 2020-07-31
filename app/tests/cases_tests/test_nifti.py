import os
import shutil
from pathlib import Path

import pytest

from grandchallenge.cases.image_builders.nifti import (
    format_error,
    image_builder_nifti,
)
from grandchallenge.cases.models import Image
from tests.cases_tests import RESOURCE_PATH


def float_close(f1: float, f2: float) -> bool:
    return abs(f1 - f2) < 0.0001


@pytest.mark.parametrize(
    "src",
    (
        RESOURCE_PATH / "image10x11x12.nii",
        RESOURCE_PATH / "image10x11x12.nii.gz",
    ),
)
def test_image_builder_fallback(tmpdir, src: Path):
    dest = Path(tmpdir) / src.name
    shutil.copy(src, dest)
    files = {Path(d[0]).joinpath(f) for d in os.walk(tmpdir) for f in d[2]}
    result = image_builder_nifti(files=files)
    assert result.consumed_files == {dest}
    assert len(result.new_images) == 1

    image = result.new_images.pop()
    assert image.color_space == Image.COLOR_SPACE_GRAY
    assert image.width == 10
    assert image.height == 11
    assert image.depth == 12
    assert float_close(image.voxel_width_mm, 1.0)
    assert float_close(image.voxel_height_mm, 2.0)
    assert float_close(image.voxel_depth_mm, 3.0)
