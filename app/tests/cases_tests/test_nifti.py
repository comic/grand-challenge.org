import os
import shutil
from pathlib import Path

import pytest

from grandchallenge.cases.image_builders.nifti import image_builder_nifti
from grandchallenge.cases.models import Image
from tests.cases_tests import RESOURCE_PATH


@pytest.mark.parametrize(
    "src",
    (
        RESOURCE_PATH / "image10x11x12.nii",
        RESOURCE_PATH / "image10x11x12.nii.gz",
    ),
)
def test_image_builder_nifti(tmpdir, src: Path):
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
    assert image.voxel_width_mm == pytest.approx(1.0)
    assert image.voxel_height_mm == pytest.approx(2.0)
    assert image.voxel_depth_mm == pytest.approx(3.0)


def test_image_builder_with_other_file_extension(tmpdir):
    dest = Path(tmpdir) / "image10x10x10.mha"
    shutil.copy(RESOURCE_PATH / dest.name, dest)
    files = {Path(d[0]).joinpath(f) for d in os.walk(tmpdir) for f in d[2]}
    result = image_builder_nifti(files=files)
    assert result.consumed_files == set()
    assert len(result.new_images) == 0
