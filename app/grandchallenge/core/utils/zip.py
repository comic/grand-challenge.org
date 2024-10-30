import io
import os
from pathlib import Path
from zipfile import ZipFile

from django.core.exceptions import SuspiciousFileOperation


def zip_memory_buffer(*, source):
    """Creates a memory-loaded ZIP archive from the content of the source"""
    source_path = Path(source)
    buffer = io.BytesIO()

    with ZipFile(buffer, "w") as zipf:
        for root, _, filenames in os.walk(source_path):
            root = Path(root)

            for filename in filenames:
                file_path = root / filename

                if source_path not in file_path.resolve().parents:
                    raise SuspiciousFileOperation(
                        "Only files under the source can be included."
                    )

                zipf.write(file_path, file_path.relative_to(source_path))

    buffer.seek(0)

    return buffer
