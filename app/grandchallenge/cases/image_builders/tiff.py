from pathlib import Path
from typing import NamedTuple, Dict

import tifffile
from django.core.exceptions import ValidationError
from django.core.files import File

from grandchallenge.cases.image_builders import ImageBuilderResult
from grandchallenge.cases.models import Image, ImageFile


class GrandChallengeTiffFile(NamedTuple):
    tifffile_tags: Dict[str, tifffile.TiffTag]
    name: str
    resolution_levels: int


def load_tiff_file(*, path: Path) -> GrandChallengeTiffFile:
    try:
        file = tifffile.TiffFile(str(path.absolute()))
        tags = file.pages[0].tags
    except ValueError:
        raise ValidationError("Image isn't a TIFF file")

    resolution_levels = len(file.pages)

    validate_tiff(tags=tags, resolution_levels=resolution_levels)

    return GrandChallengeTiffFile(
        tifffile_tags=tags, name=path.name, resolution_levels=resolution_levels
    )


def validate_tiff(
    *, tags: Dict[str, tifffile.TiffTag], resolution_levels: int
):
    required_tile_tags = (
        "TileWidth",
        "TileLength",
        "TileOffsets",
        "TileByteCounts",
    )

    forbidden_description_tags = ("dicom", "xml")

    # Checks if the image description exists, if so, ensure there's no DICOM or XML data
    try:
        image_description = str(tags["ImageDescription"].value).lower()
        for forbidden in forbidden_description_tags:
            if forbidden in image_description:
                raise ValidationError(
                    "Image contains unauthorized information"
                )
    except KeyError:
        pass

    # Fails if the image doesn't have all required tile tags
    if not all(tag in tags for tag in required_tile_tags):
        raise ValidationError("Image has incomplete tile information")

    # Fails if the image only has a single resolution page
    if resolution_levels == 1:
        raise ValidationError("Image only has a single resolution level")

    # Fails if the image doesn't have the chunky format
    if str(tags["PlanarConfiguration"].value) != "PLANARCONFIG.CONTIG":
        raise ValidationError(
            "Image planar configuration isn't configured as 'Chunky' format"
        )

    # Checks color space information
    try:
        # Fails if the color space isn't supported
        try:
            tif_color_space = get_color_space(
                str(tags["PhotometricInterpretation"].value)
            )
        except ValueError:
            raise ValidationError("Image utilizes an invalid color space")

        # Fails if the amount of bytes per sample doesn't correspond to the color space
        tif_color_channels = tags["SamplesPerPixel"].value
        if Image.COLOR_SPACE_COMPONENTS[tif_color_space] != tif_color_channels:
            raise ValidationError("Image contains invalid amount of channels.")
    except KeyError:
        ValidationError("Image lacks color space information")

    # Checks type information
    try:
        if str(tags["SampleFormat"].value[0]) == "IEEEFP":
            if tags["BitsPerSample"].value[0] != 32:
                raise ValidationError(
                    "Image data type has an invalid byte size"
                )

        elif str(tags["SampleFormat"].value[0]) == "UINT":
            if tags["BitsPerSample"].value[0] not in (8, 16, 32):
                raise ValidationError(
                    "Image data type has an invalid byte size"
                )
    except KeyError:
        raise ValidationError("Image lacks sample information")


def image_builder_tiff(path: Path) -> ImageBuilderResult:
    new_images = []
    new_image_files = []
    consumed_files = set()
    invalid_file_errors = {}

    for file_path in path.iterdir():
        try:
            tiff_file = load_tiff_file(path=file_path)

            new_images.append(create_tiff_image_entry(tiff_file=tiff_file))
            new_image_files.append(
                ImageFile(
                    image=new_images[-1],
                    image_type=ImageFile.IMAGE_TYPE_TIFF,
                    file=File(
                        open(file_path.absolute(), "rb"), name=file_path.name
                    ),
                )
            )
            consumed_files.add(file_path.name)
        except ValidationError as e:
            invalid_file_errors[file_path.name] = e.message

    return ImageBuilderResult(
        consumed_files=consumed_files,
        file_errors_map=invalid_file_errors,
        new_images=new_images,
        new_image_files=new_image_files,
    )


def create_tiff_image_entry(*, tiff_file: GrandChallengeTiffFile) -> Image:
    # Builds a new Image model item
    return Image(
        name=tiff_file.name,
        width=tiff_file.tifffile_tags["ImageWidth"].value,
        height=tiff_file.tifffile_tags["ImageLength"].value,
        depth=None,
        resolution_levels=tiff_file.resolution_levels,
        color_space=get_color_space(
            str(tiff_file.tifffile_tags["PhotometricInterpretation"].value)
        ),
    )


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
