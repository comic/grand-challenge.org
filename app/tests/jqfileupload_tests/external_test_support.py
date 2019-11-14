"""
Module containing functions supporting tests using jqfileupload. Contains
functions to create uploaded_file objects in various ways.
"""
from pathlib import Path

from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile
from tests.jqfileupload_tests.test_widgets_uploaded_file import (
    create_uploaded_file,
)


def create_file_with_content(
    filename: str, content: bytes, chunk_size=None
) -> StagedAjaxFile:
    """
    Create a StagedAjaxFile from a filename and fill it with the given content.

    Tests using this function must specify the pytest.mark.django_db marker!

    Parameters
    ----------
    filename: str
        The filename to store for the newly created uploaded file.
    content: bytes
        The contents to put into the newly uploaded file.
    chunk_size: None or int (optional)
        If chunking should be tested, this function allows to control the chunk
        size that the file is split up. Default is None and will lead to the
        file being stored as a single chunk.

    Returns
    -------
    StagedAjaxFile representing the newly created AjaxFile object
    """
    if (chunk_size is None) and (len(content) > 0):
        chunks = None
    else:
        chunks = list(range(1, len(content), chunk_size))
        if chunks[-1] != len(content) - 1:
            chunks.append(len(content) - 1)

    uuid = create_uploaded_file(
        content, client_filename=filename, chunks=chunks
    )
    return StagedAjaxFile(uuid)


def create_file_from_filepath(
    file_path: str, chunk_size=None
) -> StagedAjaxFile:
    """
    Reads the given file and creates an StagedAjaxFile from the contents
    and filename of the provided file.

    Tests using this function must specify the pytest.mark.django_db marker!

    Parameters
    ----------
    file_path: str
        The path to the file to create a new
    chunk_size: None or int (optional)
        If chunking should be tested, this function allows to control the chunk
        size that the file is split up. Default is None and will lead to the
        file being stored as a single chunk.

    Returns
    -------
    The newly created StagedAjaxFile with the contents of the file referenced
    in `file_path` and filename equal to the filename referenced in `file_path`.
    """
    file_path = Path(file_path)
    with open(file_path, "rb") as f:
        return create_file_with_content(
            file_path.name, f.read(), chunk_size=chunk_size
        )
