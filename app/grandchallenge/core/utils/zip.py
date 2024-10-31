import io
from zipfile import ZipFile

from django.core.exceptions import SuspiciousFileOperation


def zip_memory_buffer(*, source):
    """Creates a memory-loaded ZIP archive from the content of the source"""
    source = source.resolve()
    buffer = io.BytesIO()

    with ZipFile(buffer, "w") as zipf:
        for file_path in source.rglob("*"):
            if file_path.is_file():
                resolved_path = file_path.resolve()

                if source not in resolved_path.parents:
                    raise SuspiciousFileOperation(
                        "Only files under the source can be included."
                    )

                zipf.write(file_path, file_path.relative_to(source))

    buffer.seek(0)

    return buffer
