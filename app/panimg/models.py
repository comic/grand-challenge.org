from dataclasses import dataclass
from enum import Enum
from tempfile import TemporaryFile
from typing import Optional
from uuid import UUID


class ColorSpace(Enum):
    GRAY = "GRAY"
    RGB = "RGB"
    RGBA = "RGBA"
    YCBCR = "YCBCR"


class ImageType(Enum):
    MHD = "MHD"
    TIFF = "TIFF"
    DZI = "DZI"


@dataclass(frozen=True)
class PanImg:
    pk: UUID
    name: str
    width: int
    height: int
    depth: Optional[int]
    voxel_width_mm: Optional[float]
    voxel_height_mm: Optional[float]
    voxel_depth_mm: Optional[float]
    timepoints: Optional[int]
    resolution_levels: Optional[int]
    window_center: Optional[float]
    window_width: Optional[float]
    color_space: ColorSpace


@dataclass(frozen=True)
class PanImgFile:
    image_id: UUID
    image_type: ImageType
    file: TemporaryFile
    filename: str
