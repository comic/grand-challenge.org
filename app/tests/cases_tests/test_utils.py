from pathlib import Path

import SimpleITK
import pytest
from pytest import approx

from grandchallenge.cases.image_builders.metaio_utils import load_sitk_image
from grandchallenge.cases.image_builders.utils import convert_itk_to_internal
from grandchallenge.cases.models import Image
from tests.cases_tests import RESOURCE_PATH


def assert_sitk_img_equivalence(
    img: SimpleITK.Image, img_ref: SimpleITK.Image
):
    assert img.GetDimension() == img_ref.GetDimension()
    assert img.GetSize() == img_ref.GetSize()
    assert img.GetOrigin() == img_ref.GetOrigin()
    assert img.GetSpacing() == img_ref.GetSpacing()
    assert (
        img.GetNumberOfComponentsPerPixel()
        == img_ref.GetNumberOfComponentsPerPixel()
    )
    assert img.GetPixelIDValue() == img_ref.GetPixelIDValue()
    assert img.GetPixelIDTypeAsString() == img_ref.GetPixelIDTypeAsString()


@pytest.mark.parametrize(
    "image",
    (
        RESOURCE_PATH / "image3x4.mhd",
        RESOURCE_PATH / "image3x4-extra-stuff.mhd",
        RESOURCE_PATH / "image5x6x7.mhd",
        RESOURCE_PATH / "image10x10x10.mhd",
        RESOURCE_PATH / "image10x10x10.mha",
        RESOURCE_PATH / "image10x10x10-extra-stuff.mhd",
        RESOURCE_PATH / "image10x11x12x13.mhd",
        RESOURCE_PATH / "image10x11x12x13.mhd",
        RESOURCE_PATH / "image10x11x12x13-extra-stuff.mhd",
        RESOURCE_PATH / "image128x256RGB.mhd",
        RESOURCE_PATH / "image128x256x3RGB.mhd",
        RESOURCE_PATH / "image128x256x4RGB.mhd",
    ),
)
def test_convert_itk_to_internal(image: Path):
    def assert_img_properties(img: SimpleITK.Image, internal_image: Image):
        color_space = {
            1: Image.COLOR_SPACE_GRAY,
            3: Image.COLOR_SPACE_RGB,
            4: Image.COLOR_SPACE_RGBA,
        }

        assert internal_image.color_space == color_space.get(
            img.GetNumberOfComponentsPerPixel()
        )
        if img.GetDimension() == 4:
            assert internal_image.timepoints == img.GetSize()[-1]
        else:
            assert internal_image.timepoints is None
        if img.GetDepth():
            assert internal_image.depth == img.GetDepth()
            assert internal_image.voxel_depth_mm == img.GetSpacing()[2]
        else:
            assert internal_image.depth is None
            assert internal_image.voxel_depth_mm is None

        assert internal_image.width == img.GetWidth()
        assert internal_image.height == img.GetHeight()
        assert internal_image.voxel_width_mm == approx(img.GetSpacing()[0])
        assert internal_image.voxel_height_mm == approx(img.GetSpacing()[1])
        assert internal_image.resolution_levels is None

    img_ref = load_sitk_image(image)
    internal_image = convert_itk_to_internal(img_ref)
    assert_img_properties(img_ref, internal_image[0])
