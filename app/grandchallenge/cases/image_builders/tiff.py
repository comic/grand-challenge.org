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
        # Fails if the color space isn't supported
        try:
            tif_color_space = get_color_space(
                str(tif_tags["PhotometricInterpretation"].value)
            )
        except ValueError:
            raise ValidationError("Image utilizes an invalid color space")

        # Fails if the amount of bytes per sample doesn't correspond to the color space
        tif_color_channels = tif_tags["SamplesPerPixel"].value
        if Image.COLOR_SPACE_COMPONENTS[tif_color_space] != tif_color_channels:
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


def create_tiff_image_entry(file: Path) -> Image:
    # Function assumes validation was succesful

    # Reads the TIFF tags
    try:
        tiff_file = tiff_lib.TiffFile(str(file.absolute()))
        tiff_tags = tiff_file.pages[0].tags
    except ValueError:
        raise ValidationError("Image isn't a TIFF file")

    # Builds a new Image model item
    new_image = Image(
        name=file.name,
        width=tiff_tags["ImageWidth"].value,
        height=tiff_tags["ImageLength"].value,
        depth=None,
        resolution_levels=len(tiff_file.pages),
        color_space=get_color_space(
            str(tiff_tags["PhotometricInterpretation"].value)
        ),
    )
    return new_image


def get_color_space(color_space_string) -> Image.COLOR_SPACES:
    color_space_string = color_space_string.split(".")[1].upper()

    if color_space_string == "MINISBLACK":
        color_space = Image.COLOR_SPACE_GRAY
    else:
        try:
            color_space = dict(Image.COLOR_SPACES)[color_space_string]
        except KeyError:
            raise ValueError("Invalid color space")

    return color_space
