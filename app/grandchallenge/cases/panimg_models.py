# These models are extracted from panimg itself and need to be used
# in both places. It will be best to create a new python package
# for this so that it can be used by both grand challenge and panimg

from enum import Enum
from pathlib import Path
from uuid import UUID

from pydantic.dataclasses import dataclass

# NOTE: Only int8 or uint8 data types are checked for segments
# so the true maximum is 256
MAXIMUM_SEGMENTS_LENGTH = 64


class ColorSpace(str, Enum):
    GRAY = "GRAY"
    RGB = "RGB"
    RGBA = "RGBA"
    YCBCR = "YCBCR"


ITK_COLOR_SPACE_MAP = {
    1: ColorSpace.GRAY,
    3: ColorSpace.RGB,
    4: ColorSpace.RGBA,
}


class ImageType(str, Enum):
    MHD = "MHD"
    TIFF = "TIFF"
    DZI = "DZI"


class EyeChoice(str, Enum):
    OCULUS_DEXTER = "OD"
    OCULUS_SINISTER = "OS"
    UNKNOWN = "U"
    NOT_APPLICABLE = "NA"


@dataclass(frozen=True)
class PanImg:
    pk: UUID
    name: str
    width: int
    height: int
    depth: int | None
    voxel_width_mm: float | None
    voxel_height_mm: float | None
    voxel_depth_mm: float | None
    timepoints: int | None
    resolution_levels: int | None
    window_center: float | None
    window_width: float | None
    color_space: ColorSpace
    eye_choice: EyeChoice
    segments: frozenset[int] | None = None


@dataclass(frozen=True)
class PanImgFile:
    image_id: UUID
    image_type: ImageType
    file: Path
    directory: Path | None = None


@dataclass
class PanImgResult:
    new_images: set[PanImg]
    new_image_files: set[PanImgFile]
    consumed_files: set[Path]
    file_errors: dict[Path, list[str]]


@dataclass
class PostProcessorResult:
    new_image_files: set[PanImgFile]
