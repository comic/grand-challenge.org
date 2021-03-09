import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

import openslide
import pyvips
import tifffile

from panimg.exceptions import ValidationError
from panimg.models import (
    ColorSpace,
    ImageType,
    PanImg,
    PanImgFile,
    PanImgFolder,
)
from panimg.settings import DZI_TILE_SIZE
from panimg.types import ImageBuilderResult


@dataclass
class GrandChallengeTiffFile:
    path: Path
    pk: UUID = field(default_factory=uuid4)
    image_width: int = 0
    image_height: int = 0
    resolution_levels: int = 0
    color_space: Optional[ColorSpace] = None
    voxel_width_mm: float = 0
    voxel_height_mm: float = 0
    voxel_depth_mm: Optional[float] = None
    source_files: List = field(default_factory=list)
    associated_files: List = field(default_factory=list)

    def validate(self):
        if not self.image_width:
            raise ValidationError(
                "Not a valid tif: Image width could not be determined"
            )
        if not self.image_height:
            raise ValidationError(
                "Not a valid tif: Image height could not be determined"
            )
        if not self.resolution_levels:
            raise ValidationError(
                "Not a valid tif: Resolution levels not valid"
            )
        if not self.voxel_width_mm:
            raise ValidationError(
                "Not a valid tif: Voxel width could not be determined"
            )
        if not self.voxel_height_mm:
            raise ValidationError(
                "Not a valid tif: Voxel height could not be determined"
            )


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
        raise ValidationError("Invalid resolution in tiff file")


def _extract_openslide_properties(
    *, gc_file: GrandChallengeTiffFile, image: any
) -> GrandChallengeTiffFile:
    if not gc_file.voxel_width_mm and "openslide.mpp-x" in image.properties:
        gc_file.voxel_width_mm = (
            float(image.properties["openslide.mpp-x"]) / 1000
        )
    if not gc_file.voxel_height_mm and "openslide.mpp-y" in image.properties:
        gc_file.voxel_height_mm = (
            float(image.properties["openslide.mpp-y"]) / 1000
        )
    if (
        not gc_file.image_height
        and "openslide.level[0].height" in image.properties
    ):
        gc_file.image_height = int(
            image.properties["openslide.level[0].height"]
        )

    if (
        not gc_file.image_width
        and "openslide.level[0].width" in image.properties
    ):
        gc_file.image_width = int(image.properties["openslide.level[0].width"])

    if (
        not gc_file.resolution_levels
        and "openslide.level-count" in image.properties
    ):
        gc_file.resolution_levels = int(
            image.properties["openslide.level-count"]
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


def _get_color_space(*, color_space_string) -> Optional[ColorSpace]:
    color_space_string = color_space_string.split(".")[1].upper()

    if color_space_string == "MINISBLACK":
        color_space = ColorSpace.GRAY
    else:
        try:
            color_space = ColorSpace[color_space_string]
        except KeyError:
            return None

    return color_space


def _create_image_file(
    *, path: Path, image: PanImg, output_directory: Path
) -> PanImgFile:

    output_file = output_directory / f"{image.pk}{path.suffix}"

    if path.suffix.lower() == ".dzi":
        image_type = ImageType.DZI
    else:
        # TODO (jmsmkn): Create the tiff files in the correct location
        shutil.copy(src=str(path.resolve()), dst=str(output_file.resolve()))
        image_type = ImageType.TIFF

    return PanImgFile(
        image_id=image.pk, image_type=image_type, file=output_file
    )


def _load_with_tiff(
    *, gc_file: GrandChallengeTiffFile
) -> GrandChallengeTiffFile:
    tiff_file = tifffile.TiffFile(str(gc_file.path.absolute()))
    gc_file = _extract_tags(gc_file=gc_file, pages=tiff_file.pages)
    return gc_file


def _load_with_openslide(
    *, gc_file: GrandChallengeTiffFile
) -> (str, GrandChallengeTiffFile):
    open_slide_file = openslide.open_slide(str(gc_file.path.absolute()))
    gc_file = _extract_openslide_properties(
        gc_file=gc_file, image=open_slide_file
    )
    return gc_file


def _new_image_files(
    *, gc_file: GrandChallengeTiffFile, image: PanImg, output_directory: Path
) -> Set[PanImgFile]:
    new_image_files = {
        _create_image_file(
            path=gc_file.path.absolute(),
            image=image,
            output_directory=output_directory,
        )
    }

    if gc_file.source_files:
        for s in gc_file.source_files:
            new_image_files.add(
                _create_image_file(
                    path=s, image=image, output_directory=output_directory
                )
            )

    return new_image_files


def _new_folder_uploads(
    *, dzi_output: Path, image: PanImg,
) -> Set[PanImgFolder]:
    new_folder_upload = set()

    if dzi_output:
        dzi_folder_upload = PanImgFolder(
            folder=dzi_output.parent / (dzi_output.name + "_files"),
            image_id=image.pk,
        )
        new_folder_upload.add(dzi_folder_upload)

    return new_folder_upload


mirax_pattern = r"INDEXFILE\s?=\s?.|FILE_\d+\s?=\s?."
# vms (and vmu) files contain key value pairs, where the ImageFile keys
# can have the following format:
# ImageFile =, ImageFile(x,y) ImageFile(z,x,y)
vms_pattern = r"ImageFile(\(\d*,\d*(,\d)?\))?\s?=\s?.|MapFile\s?=\s?.|OptimisationFile\s?=\s?.|MacroImage\s?=\s?."


def _get_mrxs_files(mrxs_file: Path):
    # Find Slidedat.ini, which provides us with all the other file names
    name, _ = os.path.splitext(mrxs_file.name)
    slide_dat = mrxs_file.parent / name / "Slidedat.ini"
    file_matched = []
    if not slide_dat.exists():
        slide_dat = [
            f
            for f in slide_dat.parent.iterdir()
            if f.name.lower() == slide_dat.name.lower()
        ][0]
    with open(slide_dat, "r") as f:
        lines = [
            line for line in f.readlines() if re.match(mirax_pattern, line)
        ]
        for line in lines:
            original_name = line.split("=")[1].strip()
            if os.path.exists(slide_dat.parent / original_name):
                file_matched.append(slide_dat.parent / original_name)
        file_matched.append(slide_dat)
    return file_matched


def _get_vms_files(vms_file: Path):
    file_matched = []
    with open(str(vms_file.absolute()), "r") as f:
        lines = [line for line in f.readlines() if re.match(vms_pattern, line)]
        for line in lines:
            original_name = line.split("=")[1].strip()
            if os.path.exists(vms_file.parent / original_name):
                file_matched.append(vms_file.parent / original_name)
        return file_matched


def _convert(
    files: List[Path], associated_files_getter: Optional[callable], converter
) -> (List[GrandChallengeTiffFile], Dict):
    compiled_files: List[GrandChallengeTiffFile] = []
    associated_files: List[Path] = []
    errors = {}
    for file in files:
        try:
            gc_file = GrandChallengeTiffFile(file)
            if associated_files_getter:
                associated_files = associated_files_getter(gc_file.path)
            tiff_file = _convert_to_tiff(
                path=file, pk=gc_file.pk, converter=converter
            )
        except Exception as e:
            errors[file] = str(e)
            continue
        else:
            gc_file.path = tiff_file
            gc_file.associated_files = associated_files
            gc_file.associated_files.append(file)
            compiled_files.append(gc_file)
    return compiled_files, errors


def _convert_to_tiff(*, path: Path, pk: UUID, converter) -> Path:
    new_file_name = path.parent / f"{path.stem}_{str(pk)}.tif"
    image = converter.Image.new_from_file(
        str(path.absolute()), access="sequential"
    )

    # correct xres and yres if they have default value of 1
    # can be removed once updated to VIPS 8.10
    if image.get("xres") == 1 and "openslide.mpp-x" in image.get_fields():
        x_res = 1000.0 / float(image.get("openslide.mpp-x"))
        y_res = 1000.0 / float(image.get("openslide.mpp-y"))
        image = image.copy(xres=x_res, yres=y_res)

    image.write_to_file(
        str(new_file_name.absolute()),
        tile=True,
        pyramid=True,
        bigtiff=True,
        compression="jpeg",
        Q=70,
    )
    return new_file_name


def _load_gc_files(
    *, files: Set[Path], converter
) -> (List[GrandChallengeTiffFile], Dict):
    loaded_files = []
    errors = {}
    complex_file_handlers = {
        ".mrxs": _get_mrxs_files,
        ".vms": _get_vms_files,
        ".vmu": _get_vms_files,
        ".svs": None,
        ".ndpi": None,
        ".scn": None,
        ".bif": None,
    }
    for ext, handler in complex_file_handlers.items():
        complex_files = [file for file in files if file.suffix.lower() == ext]
        if len(complex_files) > 0:
            converted_files, convert_errors = _convert(
                complex_files, handler, converter
            )
            loaded_files += converted_files
            errors.update(convert_errors)

    # don't handle files that are associated files
    for file in files:
        if not any(g.path == file for g in loaded_files) and not any(
            file in g.associated_files
            for g in loaded_files
            if g.associated_files is not None
        ):
            gc_file = GrandChallengeTiffFile(file)
            loaded_files.append(gc_file)
    return loaded_files, errors


def image_builder_tiff(  # noqa: C901
    *, files: Set[Path], output_directory: Path, **_
) -> ImageBuilderResult:
    new_images = set()
    new_image_files = set()
    consumed_files = set()
    invalid_file_errors = {}
    new_folders = set()

    def format_error(message):
        return f"Tiff image builder: {message}"

    loaded_files, errors = _load_gc_files(files=files, converter=pyvips)
    for gc_file in loaded_files:
        dzi_output = None
        error = ""
        if gc_file.path in errors:
            error = errors[gc_file.path]

        # try and load image with tiff file
        try:
            gc_file = _load_with_tiff(gc_file=gc_file)
        except Exception as e:
            error += f"TIFF load error: {e}. "

        # try and load image with open slide
        try:
            gc_file = _load_with_openslide(gc_file=gc_file)
        except Exception as e:
            error += f"OpenSlide load error: {e}. "

        # validate
        try:
            gc_file.validate()
        except ValidationError as e:
            error += f"Validation error: {e}. "
            invalid_file_errors[gc_file.path] = format_error(error)
            continue

        image_out_dir = output_directory / str(gc_file.pk)
        image_out_dir.mkdir()

        image = _create_tiff_image_entry(tiff_file=gc_file)
        new_images.add(image)

        try:
            dzi_output, gc_file = _create_dzi_images(
                gc_file=gc_file, output_directory=image_out_dir
            )
        except ValidationError as e:
            error += f"DZI error: {e}. "

        new_image_files |= _new_image_files(
            gc_file=gc_file, image=image, output_directory=image_out_dir
        )
        new_folders |= _new_folder_uploads(dzi_output=dzi_output, image=image,)

        if gc_file.associated_files:
            consumed_files |= {f for f in gc_file.associated_files}
        else:
            consumed_files.add(gc_file.path)

    return ImageBuilderResult(
        consumed_files=consumed_files,
        file_errors=invalid_file_errors,
        new_images=new_images,
        new_image_files=new_image_files,
        new_folders=new_folders,
    )


def _create_tiff_image_entry(*, tiff_file: GrandChallengeTiffFile) -> PanImg:
    # Builds a new Image model item
    return PanImg(
        pk=tiff_file.pk,
        name=tiff_file.path.name,
        width=tiff_file.image_width,
        height=tiff_file.image_height,
        depth=1,
        resolution_levels=tiff_file.resolution_levels,
        color_space=tiff_file.color_space,
        voxel_width_mm=tiff_file.voxel_width_mm,
        voxel_height_mm=tiff_file.voxel_height_mm,
        voxel_depth_mm=tiff_file.voxel_depth_mm,
        timepoints=None,
        window_center=None,
        window_width=None,
    )


def _create_dzi_images(
    *, gc_file: GrandChallengeTiffFile, output_directory: Path
) -> (Path, GrandChallengeTiffFile):
    # Creates a dzi file(out.dzi) and corresponding tiles in folder {pk}_files
    dzi_output = output_directory / str(gc_file.pk)
    try:
        image = pyvips.Image.new_from_file(
            str(gc_file.path.absolute()), access="sequential"
        )
        pyvips.Image.dzsave(image, str(dzi_output), tile_size=DZI_TILE_SIZE)
        gc_file.source_files.append(
            dzi_output.parent / (dzi_output.name + ".dzi")
        )
    except Exception as e:
        raise ValidationError(f"Image can't be converted to dzi: {e}")

    return dzi_output, gc_file
