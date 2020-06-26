from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set

from grandchallenge.cases.models import FolderUpload, Image, ImageFile


@dataclass
class ImageBuilderResult:
    new_images: List[Image]
    new_image_files: List[ImageFile]
    new_folder_upload: List[FolderUpload]
    consumed_files: List[Path]
    file_errors_map: Dict[Path, str]


@dataclass
class ImporterResult:
    new_images: Set[Image]
    consumed_files: Set[Path]
    file_errors: Dict[str, List[str]]
