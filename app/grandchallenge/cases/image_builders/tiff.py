from pathlib import Path
from tempfile import TemporaryFile
from typing import NamedTuple
from uuid import uuid4

import pyvips
import tifffile
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File

from grandchallenge.cases.image_builders import ImageBuilderResult
from grandchallenge.cases.models import FolderUpload, Image, ImageFile


class GrandChallengeTiffFileTags(NamedTuple):
    image_width: int
    image_height: int
    resolution_levels: int
    color_space: str


class GrandChallengeTiffFile(NamedTuple):
    path: Path
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

    return GrandChallengeTiffFile(path=path, tags=tags)


def _validate_tifffile(  # noqa: C901
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

    # Fails if the color space isn't supported
    try:
        color_space = get_color_space(
            str(tags["PhotometricInterpretation"].value)
        )
    except KeyError:
        raise ValidationError("Image lacks color space information")

    # Fails if the amount of bytes per sample doesn't correspond to the
    # colour space
    tif_color_channels = tags["SamplesPerPixel"].value
    if Image.COLOR_SPACE_COMPONENTS[color_space] != tif_color_channels:
        raise ValidationError("Image contains invalid amount of channels.")

    try:
        image_width = tags["ImageWidth"].value
        image_height = tags["ImageLength"].value
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
    new_folder_upload = []

    for file_path in path.iterdir():
        pk = uuid4()

        try:
            tiff_file = load_tiff_file(path=file_path)
            dzi_output = create_dzi_images(tiff_file=tiff_file, pk=pk)
        except ValidationError as e:
            invalid_file_errors[file_path.name] = str(e)
            continue

        image = create_tiff_image_entry(tiff_file=tiff_file, pk=pk)

        temp_file = TemporaryFile()
        with open(tiff_file.path.absolute(), "rb") as open_file:
            buffer = True
            while buffer:
                buffer = open_file.read(1024)
                temp_file.write(buffer)

        new_image_files.append(
            ImageFile(
                image=image,
                image_type=ImageFile.IMAGE_TYPE_TIFF,
                file=File(temp_file, name=f"{image.pk}.tif"),
            )
        )

        temp_dzi_file = TemporaryFile()
        with open(dzi_output + ".dzi", "rb") as open_file:
            buffer = True
            while buffer:
                buffer = open_file.read(1024)
                temp_dzi_file.write(buffer)

        new_image_files.append(
            ImageFile(
                image=image,
                image_type=ImageFile.IMAGE_TYPE_DZI,
                file=File(temp_dzi_file, name=f"{image.pk}.dzi"),
            )
        )

        dzi_folder_upload = FolderUpload(
            folder=dzi_output + "_files", image=image
        )
        new_images.append(image)
        consumed_files.add(tiff_file.path.name)
        new_folder_upload.append(dzi_folder_upload)

    return ImageBuilderResult(
        consumed_files=consumed_files,
        file_errors_map=invalid_file_errors,
        new_images=new_images,
        new_image_files=new_image_files,
        new_folder_upload=new_folder_upload,
    )


def create_tiff_image_entry(*, tiff_file: GrandChallengeTiffFile, pk) -> Image:
    # Builds a new Image model item
    return Image(
        pk=pk,
        name=tiff_file.path.name,
        width=tiff_file.tags.image_width,
        height=tiff_file.tags.image_height,
        depth=1,
        resolution_levels=tiff_file.tags.resolution_levels,
        color_space=tiff_file.tags.color_space,
        eye_choice=Image.EYE_UNKNOWN,
        stereoscopic_choice=Image.STEREOSCOPIC_UNKNOWN,
        field_of_view=Image.FOV_UNKNOWN,
    )


def create_dzi_images(*, tiff_file: GrandChallengeTiffFile, pk) -> str:
    # Creates a dzi file(out.dzi) and corresponding tiles in folder {pk}_files
    dzi_output = str(tiff_file.path.parent / str(pk))
    try:
        image = pyvips.Image.new_from_file(
            str(tiff_file.path.absolute()), access="sequential"
        )

        pyvips.Image.dzsave(
            image, dzi_output, tile_size=settings.DZI_TILE_SIZE
        )
    except Exception as e:
        raise ValidationError("Image can't be converted to dzi: " + str(e))

    return dzi_output
