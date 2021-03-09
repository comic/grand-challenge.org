from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set

from panimg.models import PanImg, PanImgFile, PanImgFolder


@dataclass
class ImageBuilderResult:
    new_images: Set[PanImg]
    new_image_files: Set[PanImgFile]
    new_folders: Set[PanImgFolder]
    consumed_files: Set[Path]
    file_errors: Dict[Path, str]


@dataclass
class PanimgResult(ImageBuilderResult):
    file_errors: Dict[Path, List[str]]
