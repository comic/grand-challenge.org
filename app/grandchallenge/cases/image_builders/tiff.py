"""
Image builder for TIFF files.
"""
import tifffile as tiff_lib

from pathlib import Path
from django.core.exceptions import ValidationError
from django.core.files import File

from grandchallenge.cases.image_builders import ImageBuilderResult
from grandchallenge.cases.models import Image, ImageFile


def image_builder_tiff(path: Path) -> ImageBuilderResult:
    new_images = []
    new_image_files = []
    consumed_files = set()
    invalid_file_errors = {}

    for file in path.iterdir():
        try:
            validate_tiff(file.absolute())

            new_images.append(create_tiff_image_entry(file))
            new_image_files.append(
                ImageFile(
                    image=new_images[-1],
                    image_type=ImageFile.IMAGE_TYPE_TIFF,
                    file=File(open(file.absolute(), "rb"), name=file.name),
                )
            )
            consumed_files.add(file.name)
        except ValidationError as e:
            invalid_file_errors[file.name] = e.message

    return ImageBuilderResult(
        consumed_files=consumed_files,
        file_errors_map=invalid_file_errors,
        new_images=new_images,
        new_image_files=new_image_files,
    )


def validate_tiff(path: Path):
    # Model names and color channels
    accepted_color_models = {
        "PHOTOMETRIC.MINISBLACK": 1,
        "PHOTOMETRIC.RGB": 3,
        "PHOTOMETRIC.ARGB": 4,
        "PHOTOMETRIC.YCBCR": 4,
    }

    required_tile_tags = (
        "TileWidth",
        "TileLength",
        "TileOffsets",
        "TileByteCounts",
    )

    forbidden_description_tags = ("dicom", "xml")

    # Reads the TIF tags
    try:
        tif_file = tiff_lib.TiffFile(str(path))
        tif_tags = tif_file.pages[0].tags
    except ValueError:
        raise ValidationError("Image isn't a TIFF file")

    # Checks if the image description exists, if so, ensure there's no DICOM or XML data
    try:
        image_description = str(tif_tags["ImageDescription"].value).lower()
        for forbidden in forbidden_description_tags:
            if forbidden in image_description:
                raise ValidationError(
                    "Image contains unauthorized information"
                )
    except KeyError:
        pass

    # Fails if the image doesn't have all required tile tags
    if not all(tag in tif_tags for tag in required_tile_tags):
        raise ValidationError("Image has incomplete tile information")

    # Fails if the image only has a single resolution page
    if len(tif_file.pages) == 1:
        raise ValidationError("Image only has a single resolution level")

    # Fails if the image doesn't have the chunky format
    if str(tif_tags["PlanarConfiguration"].value) != "PLANARCONFIG.CONTIG":
        raise ValidationError(
            "Image planar configuration isn't configured as 'Chunky' format"
        )

    # Checks color space information
    try:
        # Fails if the color space model isn't supported
        tif_color_model = str(tif_tags["PhotometricInterpretation"].value)
        if tif_color_model not in accepted_color_models:
            raise ValidationError("Image utilizes an invalid color model")

        # Fails if the amount of bytes per sample doesn't correspond to the color model
        tif_color_channels = tif_tags["SamplesPerPixel"].value
        if accepted_color_models[tif_color_model] != tif_color_channels:
            raise ValidationError("Image contains invalid amount of channels.")
    except KeyError:
        ValidationError("Image lacks color space information")

    # Checks type information
    try:
        if str(tif_tags["SampleFormat"].value[0]) == "IEEEFP":
            if tif_tags["BitsPerSample"].value[0] != 32:
                raise ValidationError(
                    "Image data type has an invalid byte size"
                )

        elif str(tif_tags["SampleFormat"].value[0]) == "UINT":
            if tif_tags["BitsPerSample"].value[0] not in (8, 16, 32):
                raise ValidationError(
                    "Image data type has an invalid byte size"
                )
    except KeyError:
        raise ValidationError("Image lacks sample information")


def create_tiff_image_entry(file: Path):
    # Reads the TIFF tags
    try:
        tiff_file = tiff_lib.TiffFile(str(file.absolute()))
        tiff_tags = tiff_file.pages[0].tags
    except ValueError:
        raise ValidationError("Image isn't a TIFF file")

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
    )
    return new_image
