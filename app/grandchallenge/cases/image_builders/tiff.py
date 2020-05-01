from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryFile
from typing import Optional
from uuid import UUID, uuid4

import openslide
import pyvips
import tifffile
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File

from grandchallenge.cases.image_builders import ImageBuilderResult
from grandchallenge.cases.models import FolderUpload, Image, ImageFile


@dataclass
class GrandChallengeTiffFile:
    path: Path
    image_width: int = 0
    image_height: int = 0
    resolution_levels: int = 0
    color_space: str = ""
    voxel_width_mm: float = 0
    voxel_height_mm: float = 0
    voxel_depth_mm: Optional[float] = None

    def validate(self):
        if not self.image_width:
            raise ValidationError("ImageWidth could not be determined")
        if not self.image_height:
            raise ValidationError("ImageHeigth could not be determined")
        if not self.resolution_levels:
            raise ValidationError("Resolution levels not valid")
        if not self.color_space:
            raise ValidationError("ColorSpace not valid")
        if not self.voxel_width_mm:
            raise ValidationError("Voxel width could not be determined")
        if not self.voxel_height_mm:
            raise ValidationError("Voxel height could not be determined")


def _get_tag_value(tags, tag):
    try:
        return tags[tag].value
    except (KeyError, AttributeError):
        return None


def _get_voxel_spacing_mm(tags, tag):
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
        resolution_unit = str(_get_tag_value(tags, "ResolutionUnit"))
        resolution = _get_tag_value(tags, tag)
        if resolution_unit == "RESUNIT.INCH":
            return 25.4 / (resolution[0] / resolution[1])
        elif resolution_unit == "RESUNIT.CENTIMETER":
            return 10 / (resolution[0] / resolution[1])
        raise ValidationError(
            f"Invalid resolution unit {resolution_unit}" f" in tiff file"
        )
    except (ZeroDivisionError, TypeError, IndexError):
        raise ValidationError(f"Invalid resolution in tiff file")


def _extract_openslide_properties(
    *, gc_file: GrandChallengeTiffFile, image: any
):
    if not gc_file.voxel_width_mm and "openslide.mpp-x" in image.properties:
        gc_file.voxel_width_mm = (
            float(image.properties["openslide.mpp-x"]) / 1000
        )
    if not gc_file.voxel_height_mm and "openslide.mpp-y" in image.properties:
        gc_file.voxel_height_mm = (
            float(image.properties["openslide.mpp-y"]) / 1000
        )
    return gc_file


def _extract_tags(
    *, gc_file: GrandChallengeTiffFile, pages: tifffile.tifffile.TiffPages
) -> GrandChallengeTiffFile:
    """
    Extracts tags form a tiff file loaded with tifffile for use in grand challenge
    :param pages: The pages and tags from tifffile
    :return: The GrandChallengeTiffFile with the properties defined in the tags
    """
    if not pages:
        return gc_file

    tags = pages[0].tags

    gc_file.resolution_levels = len(pages)

    gc_file.color_space = _get_color_space(
        color_space_string=str(
            _get_tag_value(tags, "PhotometricInterpretation")
        )
    )
    gc_file.image_width = _get_tag_value(tags, "ImageWidth")
    gc_file.image_height = _get_tag_value(tags, "ImageLength")

    #  some formats like the Philips tiff don't have the spacing in their tags,
    #  we retrieve them later with OpenSlide
    if "XResolution" in tags:
        gc_file.voxel_width_mm = _get_voxel_spacing_mm(tags, "XResolution")
        gc_file.voxel_height_mm = _get_voxel_spacing_mm(tags, "YResolution")

    gc_file.voxel_depth_mm = None

    return gc_file


def _get_color_space(*, color_space_string) -> Image.COLOR_SPACES:
    color_space_string = color_space_string.split(".")[1].upper()

    if color_space_string == "MINISBLACK":
        color_space = Image.COLOR_SPACE_GRAY
    else:
        try:
            color_space = dict(Image.COLOR_SPACES)[color_space_string]
        except KeyError:
            return None

    return color_space


def _create_image_file(*, path: str, image: Image):
    temp_file = TemporaryFile()
    with open(path, "rb") as open_file:
        buffer = True
        while buffer:
            buffer = open_file.read(1024)
            temp_file.write(buffer)

    if path.lower().endswith("dzi"):
        return ImageFile(
            image=image,
            image_type=ImageFile.IMAGE_TYPE_DZI,
            file=File(temp_file, name=f"{image.pk}.dzi"),
        )
    else:
        return ImageFile(
            image=image,
            image_type=ImageFile.IMAGE_TYPE_TIFF,
            file=File(temp_file, name=f"{image.pk}.tif"),
        )


def _load_with_tiff(*, gc_file: GrandChallengeTiffFile):
    tiff_file = tifffile.TiffFile(str(gc_file.path.absolute()))
    gc_file = _extract_tags(gc_file=gc_file, pages=tiff_file.pages)
    return tiff_file, gc_file


def _load_with_open_slide(*, gc_file: GrandChallengeTiffFile, pk: UUID):
    open_slide_file = openslide.open_slide(str(gc_file.path.absolute()))
    gc_file = _extract_openslide_properties(
        gc_file=gc_file, image=open_slide_file
    )
    gc_file.validate()
    dzi_output = _create_dzi_images(gc_file=gc_file, pk=pk)
    return dzi_output, gc_file


def _add_image_files(
    *, tiff_file, gc_file, dzi_output, image, new_image_files
):
    if tiff_file:
        new_image_files.append(
            _create_image_file(path=str(gc_file.path.absolute()), image=image)
        )

    if dzi_output:
        new_image_files.append(
            _create_image_file(path=dzi_output + ".dzi", image=image)
        )
    return new_image_files


def _add_folder_uploads(*, dzi_output, image, new_folder_upload):
    if dzi_output:
        dzi_folder_upload = FolderUpload(
            folder=dzi_output + "_files", image=image
        )
        new_folder_upload.append(dzi_folder_upload)
    return new_folder_upload


def image_builder_tiff(path: Path, session_id=None) -> ImageBuilderResult:
    new_images = []
    new_image_files = []
    consumed_files = set()
    invalid_file_errors = {}
    new_folder_upload = []

    def format_error(message):
        return f"Tiff image builder: {message}"

    for file_path in path.iterdir():
        pk = uuid4()
        dzi_output = None
        tiff_file = None
        gc_file = GrandChallengeTiffFile(file_path)

        # try and load image with tiff file
        try:
            tiff_file, gc_file = _load_with_tiff(gc_file=gc_file)
        except Exception as e:
            invalid_file_errors[file_path.name] = format_error(e)

        # try and load image with open_slide
        try:
            dzi_output, gc_file = _load_with_open_slide(gc_file=gc_file, pk=pk)
        except Exception as e:
            invalid_file_errors[file_path.name] = format_error(e)

        # validate
        try:
            gc_file.validate()
            if not tiff_file and not dzi_output:
                raise ValidationError(
                    "File could not be opened by either TIFFILE or OpenSlide"
                )
        except ValidationError as e:
            invalid_file_errors[file_path.name] = format_error(e)
            continue

        image = _create_tiff_image_entry(tiff_file=gc_file, pk=pk)
        new_image_files = _add_image_files(
            tiff_file=tiff_file,
            gc_file=gc_file,
            dzi_output=dzi_output,
            image=image,
            new_image_files=new_image_files,
        )

        new_folder_upload = _add_folder_uploads(
            dzi_output=dzi_output,
            image=image,
            new_folder_upload=new_folder_upload,
        )
        new_images.append(image)
        consumed_files.add(gc_file.path.name)

    return ImageBuilderResult(
        consumed_files=consumed_files,
        file_errors_map=invalid_file_errors,
        new_images=new_images,
        new_image_files=new_image_files,
        new_folder_upload=new_folder_upload,
    )


def _create_tiff_image_entry(
    *, tiff_file: GrandChallengeTiffFile, pk: UUID
) -> Image:
    # Builds a new Image model item
    return Image(
        pk=pk,
        name=tiff_file.path.name,
        width=tiff_file.image_width,
        height=tiff_file.image_height,
        depth=1,
        resolution_levels=tiff_file.resolution_levels,
        color_space=tiff_file.color_space,
        eye_choice=Image.EYE_UNKNOWN,
        stereoscopic_choice=Image.STEREOSCOPIC_UNKNOWN,
        field_of_view=Image.FOV_UNKNOWN,
        voxel_width_mm=tiff_file.voxel_width_mm,
        voxel_height_mm=tiff_file.voxel_height_mm,
        voxel_depth_mm=tiff_file.voxel_depth_mm,
    )


def _create_dzi_images(*, gc_file: GrandChallengeTiffFile, pk: UUID) -> str:
    # Creates a dzi file(out.dzi) and corresponding tiles in folder {pk}_files
    dzi_output = str(gc_file.path.parent / str(pk))
    try:
        image = pyvips.Image.new_from_file(
            str(gc_file.path.absolute()), access="sequential"
        )
        pyvips.Image.dzsave(
            image, dzi_output, tile_size=settings.DZI_TILE_SIZE
        )
    except Exception as e:
        raise ValidationError(f"Image can't be converted to dzi: {e}")

    return dzi_output
