"""
Module containing functions supporting tests using jqfileupload. Contains
functions to create uploaded_file objects in various ways.
"""
import random
from pathlib import Path
from typing import Optional, Sequence, overload

from django.http import HttpResponse, HttpRequest
from django.test import Client, RequestFactory

from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile
from tests.jqfileupload_tests.test_widgets_uploaded_file import (
    create_uploaded_file
)
from tests.jqfileupload_tests.utils import (
    create_upload_file_request,
    create_partial_upload_file_request,
)


def create_file_with_content(
    filename: str, content: bytes, chunk_size=None
) -> StagedAjaxFile:
    """
    This function creates a StagedAjaxFile from a filename and fills it with
    the provided contents.

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


class UploadSession:
    """
    This class generates a new upload session allowing to upload multiple files
    as one session through the ajax interface.

    This mainly involves the creation of a new csrf_token which is remembered
    and used for every upload request.  
    """

    def __init__(self, sender):
        self.__upload_counter = 0
        self.__csrf_token = f"{__file__}" f"-{id(sender)}" f"-{hex(random.randint(0, 1000000000000000000))[2:]}"

    @overload
    def single_chunk_upload(
        self, client: Client, filename: str, content: bytes, endpoint: str
    ) -> HttpResponse:
        ...

    @overload
    def single_chunk_upload(
        self,
        client: RequestFactory,
        filename: str,
        content: bytes,
        endpoint: str,
    ) -> HttpRequest:
        ...

    def single_chunk_upload(self, client, filename, content, endpoint):
        """
        Executes a single-chunk upload with the given content. In contrast to
        the `create_file_*` functions, this function utilizes the django-router and
        operates on the AJAX-API, resulting in a more expensive, but also more
        rigid test.

        Parameters
        ----------
        client: Client
            Django test client to use to make conenctions,
        filename: str
            The filename of the uploaded file
        content: bytes
            The content of the file
        endpoint: str
            URL the url to upload to

        Returns
        -------
        HttpResponse resulting from the request.
        """
        return create_upload_file_request(
            client,
            filename=filename,
            content=content,
            url=endpoint,
            csrf_token=self.__csrf_token,
        )

    @overload
    def multi_chunk_upload(
        self,
        client: Client,
        filename: str,
        content: bytes,
        endpoint: str,
        chunks: int = 1,
    ) -> Sequence[HttpResponse]:
        ...

    @overload
    def multi_chunk_upload(
        self,
        client: RequestFactory,
        filename: str,
        content: bytes,
        endpoint: str,
        chunks: int = 1,
    ) -> Sequence[HttpRequest]:
        ...

    def multi_chunk_upload(self, client, filename, content, endpoint, chunks):
        """
        Executes a multi-chunk upload with the given content. The chunks option
        allows to specify how many equally sized chunks should be sent. If not
        specified, the default is to use send a single chunk, but still utilize
        chunked uploading.

        Parameters
        ----------
        client: Client
            Django test client to use to make conenctions,
        filename: str
            The filename of the uploaded file
        content: bytes
            The content of the file
        endpoint: str
            URL the url to upload to

        Other Parameters
        ----------------
        chunks: int
            The number of chunks to use for sending content. Defaults to 1.

        Returns
        -------
        A list of HttpResponse objects for each submitted chunk.
        """
        self.__upload_counter += 1
        upload_identifier = f"{self.__csrf_token}_{self.__upload_counter}"

        chunk_ends = list(range(0, len(content), len(content) // chunks))[
            1:
        ] + [len(content)]
        result = []
        start = 0
        for end in chunk_ends:
            result.append(
                create_partial_upload_file_request(
                    client,
                    upload_identifier,
                    content,
                    start,
                    end,
                    filename,
                    url=endpoint,
                    csrf_token=self.__csrf_token,
                )
            )
            start = end
        return tuple(result)
