"""
Image builder for TIFF files.
"""

from pathlib import Path
from django.core.files import File

import tifffile as tiff_lib
import traceback

from grandchallenge.cases.image_builders import ImageBuilderResult
from grandchallenge.cases.models import Image, ImageFile


def image_builder_tiff(path: Path) -> ImageBuilderResult:
    new_images = []
    new_image_files = []
    consumed_files = set()
    invalid_file_errors = {}

    for file in path.iterdir():
        valid, message = validate_tiff(file.absolute())

        if not valid:
            invalid_file_errors[file.name] = message
        else:

            new_images.append(CreateTiffImageEntry(file))
            new_image_files.append(ImageFile(image=new_images[-1], file=File(file, name=file.name)))
            consumed_files.add(file.name)

    return ImageBuilderResult(
        consumed_files=consumed_files,
        file_errors_map=invalid_file_errors,
        new_images=new_images,
        new_image_files=new_image_files, )


def validate_tiff(path: Path):
    accepted_color_models = {"PHOTOMETRIC.MINISBLACK": 1,
                             "PHOTOMETRIC.RGB": 3,
                             "PHOTOMETRIC.ARGB": 4,
                             "PHOTOMETRIC.YCBCR": 4, }

    required_tile_tags = ("TileWidth",
                          "TileLength",
                          "TileOffsets",
                          "TileByteCounts",)

    forbidden_description_tags = ("DICOM",
                                  "XML",
                                  "xml",)

    try:
        # Reads the TIF tags
        tif_file = tiff_lib.TiffFile(str(path))
        tif_tags = tif_file.pages[0].tags

        # Checks if the image description exists, if so, ensure there's no DICOM or XML data
        if "ImageDescription" in tif_tags:
            image_description = str(tif_tags["ImageDescription"].value)
            for forbidden in forbidden_description_tags:
                if forbidden in image_description:
                    return False, "Image contains unauthorized information"

        # Checks image storage information
        for tag in required_tile_tags:
            if tag not in tif_tags.keys():
                return False, "Image has incomplete tile information"

        if len(tif_file.pages) == 1:
            return False, "Image only has a single resolution level"

        if str(tif_tags["PlanarConfiguration"].value) != "PLANARCONFIG.CONTIG":
            return False, "Image planar configuration isn't configured as 'Chunky' format"

        # Checks colour model information
        if str(tif_tags["PhotometricInterpretation"].value) not in accepted_color_models:
            return False, "Image utilizes an invalid color model"

        if (accepted_color_models[str(tif_tags["PhotometricInterpretation"].value)]
                != tif_tags["SamplesPerPixel"].value):
            return False, ""

        # Check type information
        if str(tif_tags["SampleFormat"].value[0]) == "IEEEFP":
            if tif_tags["BitsPerSample"].value[0] != 32:
                return False, "Image data type has an invalid byte size"
        elif str(tif_tags["SampleFormat"].value[0]) == "UINT":
            if tif_tags["BitsPerSample"].value[0] not in (8, 16, 32):
                return False, "Image data type has an invalid byte size"

        return True, ""
    except Exception as e:
        traceback.print_exc()
        return False, str(e)


def CreateTiffImageEntry(file):
    # Reads the TIFF tags
    tiff_file = tiff_lib.TiffFile(file.absolute)
    tiff_tags = tiff_file.pages[0].tags

    # Detects the color space and formats it correctly
    color_space = str(tiff_tags["PhotometricInterpretation"].value)

    if color_space == "PHOTOMETRIC.YCBCR":
        color_space = "YCBCR"
    else:
        color_space = color_space.split(".")[1]

    # Builds a new Image model item
    new_image = Image(
        name=file.name,
        width=tiff_tags["ImageWidth"].value,
        height=tiff_tags["ImageLength"].value,
        depth=None,
        resolution_levels=len(tiff_file.pages),
        color_space=color_space,
        image_type="TIFF"
    )
    return new_image
