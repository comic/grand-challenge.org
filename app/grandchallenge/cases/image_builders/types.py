from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from grandchallenge.cases.models import Image, ImageFile


@dataclass
class ImageBuilderResult:
    consumed_files: List[Path]
    file_errors_map: Dict[Path, str]
    new_images: List[Image]
    new_image_files: List[ImageFile]
    new_folder_upload: List
