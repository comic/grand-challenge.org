from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set

from grandchallenge.cases.models import Image


@dataclass
class ImporterResult:
    new_images: Set[Image]
    consumed_files: Set[Path]
    file_errors: Dict[Path, List[str]]
