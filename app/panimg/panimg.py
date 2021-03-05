from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable, Optional, Set

from panimg.image_builders import DEFAULT_IMAGE_BUILDERS
from panimg.types import ImageBuilderResult, PanimgResult


def convert(
    *,
    files: Set[Path],
    output_directory: Path,
    builders: Optional[Iterable[Callable]] = None,
    created_image_prefix: str = "",
) -> PanimgResult:
    new_images = set()
    new_image_files = set()
    new_folders = set()
    consumed_files = set()
    file_errors = defaultdict(list)

    builders = builders if builders is not None else DEFAULT_IMAGE_BUILDERS

    for builder in builders:
        builder_result: ImageBuilderResult = builder(
            files=files - consumed_files,
            output_directory=output_directory,
            created_image_prefix=created_image_prefix,
        )

        new_images |= builder_result.new_images
        new_image_files |= builder_result.new_image_files
        new_folders |= builder_result.new_folders
        consumed_files |= builder_result.consumed_files

        for filepath, msg in builder_result.file_errors.items():
            file_errors[filepath].append(msg)

    return PanimgResult(
        new_images=new_images,
        new_image_files=new_image_files,
        new_folders=new_folders,
        consumed_files=consumed_files,
        file_errors={**file_errors},
    )
