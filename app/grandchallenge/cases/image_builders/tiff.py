from pathlib import Path
from typing import NamedTuple

import tifffile
from django.core.exceptions import ValidationError
from django.core.files import File

from grandchallenge.cases.image_builders import ImageBuilderResult
from grandchallenge.cases.models import Image, ImageFile


class GrandChallengeTiffFileTags(NamedTuple):
    image_width: int
    image_height: int
    resolution_levels: int
    color_space: str


class GrandChallengeTiffFile(NamedTuple):
    name: str
    tags: GrandChallengeTiffFileTags


def load_tiff_file(*, path: Path) -> GrandChallengeTiffFile:
    """
    Loads and validates a file using tifffile
    :param path: The path to the potential tiff file
    :return: A tiff file that can be used in the rest of grand challenge
    """
    try:
        file = tifffile.TiffFile(str(path.absolute()))
    except ValueError:
        raise ValidationError("Image isn't a TIFF file")

    tags = _validate_tifffile(pages=file.pages)

    return GrandChallengeTiffFile(name=path.name, tags=tags)


def _validate_tifffile(
    *, pages: tifffile.tifffile.TiffPages
) -> GrandChallengeTiffFileTags:
    """
    Validates a tiff file loaded with tifffile for use in grand challenge
    :param pages: The pages and tags from tiffile
    :return: The extracted tags that are needed by the rest of the framework
    """
    required_tile_tags = ("TileOffsets", "TileByteCounts")

    forbidden_description_tags = ("dicom", "xml")

    tags = pages[0].tags

    # Checks if the image description exists,
    # if so, ensure there's no DICOM or XML data
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
    resolution_levels = len(pages)
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

        # Fails if the amount of bytes per sample doesn't correspond to the
        # colour space
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

    try:
        image_width = tags["ImageWidth"].value
        image_height = tags["ImageLength"].value
        color_space = get_color_space(
            str(tags["PhotometricInterpretation"].value)
        )
    except KeyError:
        raise ValidationError("Missing tags in tiff file")

    return GrandChallengeTiffFileTags(
        image_width=image_width,
        image_height=image_height,
        color_space=color_space,
        resolution_levels=resolution_levels,
    )


def get_color_space(color_space_string) -> Image.COLOR_SPACES:
    color_space_string = color_space_string.split(".")[1].upper()

    if color_space_string == "MINISBLACK":
        color_space = Image.COLOR_SPACE_GRAY
    else:
        try:
            color_space = dict(Image.COLOR_SPACES)[color_space_string]
        except KeyError:
            raise ValidationError("Invalid color space")

    return color_space


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
        width=tiff_file.tags.image_width,
        height=tiff_file.tags.image_height,
        depth=None,
        resolution_levels=tiff_file.tags.resolution_levels,
        color_space=tiff_file.tags.color_space,
    )
