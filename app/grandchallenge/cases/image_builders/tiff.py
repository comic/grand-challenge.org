from pathlib import Path
from tempfile import TemporaryFile
from typing import NamedTuple, Union
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
    voxel_width_mm: float
    voxel_height_mm: float
    voxel_depth_mm: Union[float, None]


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

    def get_tag_value(tags, tag, required=True):
        try:
            return tags[tag].value
        except KeyError:
            if required:
                raise ValidationError(
                    f"Tiff file is missing required tag {tag}"
                )

    def get_voxel_spacing_mm(tags, tag):
        """
        Calculate the voxel spacing in mm.

        Use the set of tags from the tiff image to calculate the spacing for a
        particular dimension. Supports INCH and CENTIMETER resolution units.

        Parameters
        ----------
        tags
            The collection of tags from the tif file.
        tag
            The tag that contains the resolution of the tif file along the
            dimension of interest.

        Raises
        ------
        ValidationError
            Raised if an unrecognised resolution unit is used.


        Returns
        -------
            The voxel spacing in mm.

        """
        try:
            # Resolution is a tuple of the number of pixels and the length of the
            # image in cm or inches, depending on resolution unit
            resolution_unit = str(get_tag_value(tags, "ResolutionUnit"))
            resolution = get_tag_value(tags, tag)
            if resolution_unit == "RESUNIT.INCH":
                return 25.4 / (resolution[0] / resolution[1])
            elif resolution_unit == "RESUNIT.CENTIMETER":
                return 10 / (resolution[0] / resolution[1])
            raise ValidationError(
                f"Invalid resolution unit {resolution_unit}" f" in tiff file"
            )
        except ZeroDivisionError:
            raise ValidationError(f"Invalid resolution in tiff file")

    required_tile_tags = ("TileOffsets", "TileByteCounts")

    forbidden_description_tags = ("dicom", "xml")

    tags = pages[0].tags

    # Checks if the image description exists,
    # if so, ensure there's no DICOM or XML data
    image_description = str(
        get_tag_value(tags, "ImageDescription", False)
    ).lower()
    for forbidden in forbidden_description_tags:
        if forbidden in image_description:
            raise ValidationError("Image contains unauthorized information")

    # Fails if the image doesn't have all required tile tags
    for tag in required_tile_tags:
        get_tag_value(tags, tag, True)

    # Fails if the image only has a single resolution page
    resolution_levels = len(pages)
    if resolution_levels == 1:
        raise ValidationError("Image only has a single resolution level")

    # Fails if the image doesn't have the chunky format
    if (
        str(get_tag_value(tags, "PlanarConfiguration"))
        != "PLANARCONFIG.CONTIG"
    ):
        raise ValidationError(
            "Image planar configuration isn't configured as 'Chunky' format"
        )

    # Fails if the color space isn't supported
    color_space = get_color_space(
        str(get_tag_value(tags, "PhotometricInterpretation"))
    )

    # Fails if the amount of bytes per sample doesn't correspond to the
    # colour space
    tif_color_channels = get_tag_value(tags, "SamplesPerPixel")
    if Image.COLOR_SPACE_COMPONENTS[color_space] != tif_color_channels:
        raise ValidationError("Image contains invalid amount of channels.")

    voxel_width_mm = get_voxel_spacing_mm(tags, "XResolution")
    voxel_height_mm = get_voxel_spacing_mm(tags, "YResolution")
    image_width = get_tag_value(tags, "ImageWidth")
    image_height = get_tag_value(tags, "ImageLength")

    return GrandChallengeTiffFileTags(
        image_width=image_width,
        image_height=image_height,
        color_space=color_space,
        resolution_levels=resolution_levels,
        voxel_width_mm=voxel_width_mm,
        voxel_height_mm=voxel_height_mm,
        voxel_depth_mm=None,
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
        dzi_output = None
        try:
            tiff_file = load_tiff_file(path=file_path)
        except ValidationError as e:
            invalid_file_errors[file_path.name] = e.message  # noqa: B306
            continue

        try:
            dzi_output = create_dzi_images(tiff_file=tiff_file, pk=pk)
        except ValidationError as e:
            invalid_file_errors[file_path.name] = e.message  # noqa: B306

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

        if dzi_output:
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
            new_folder_upload.append(dzi_folder_upload)

        new_images.append(image)
        consumed_files.add(tiff_file.path.name)

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
        voxel_width_mm=tiff_file.tags.voxel_width_mm,
        voxel_height_mm=tiff_file.tags.voxel_height_mm,
        voxel_depth_mm=tiff_file.tags.voxel_depth_mm,
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
