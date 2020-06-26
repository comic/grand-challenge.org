from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set

from grandchallenge.cases.models import FolderUpload, Image, ImageFile


@dataclass
class ImageBuilderResult:
    new_images: Set[Image]
    new_image_files: Set[ImageFile]
    new_folder_upload: Set[FolderUpload]
    consumed_files: Set[Path]
    file_errors_map: Dict[Path, str]


@dataclass
class ImporterResult:
    new_images: Set[Image]
    consumed_files: Set[Path]
    file_errors: Dict[str, List[str]]
