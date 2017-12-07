import pytest

import uuid
from io import BytesIO

from datetime import timedelta

from django.core import files
from django.utils import timezone

from evaluation.models import StagedFile
from evaluation.widgets.uploader import UploadedAjaxFileList, StagedAjaxFile, \
    cleanup_stale_files


def create_uploaded_file(
        content: str,
        chunks=None,
        csrf="test_csrf",
        client_id="test_client_id",
        client_filename="test_client_filename_{uuid}",
        timeout=timedelta(minutes=1)) -> uuid.UUID:
    if chunks is None:
        chunks = [len(string)]

    new_uuid = uuid.uuid4()
    client_filename = client_filename.format(uuid=new_uuid)

    start = 0
    for chunk in chunks:
        staged_file = StagedFile(
            csrf=csrf,
            client_id=client_id,
            client_filename=client_filename,
            file_id=new_uuid,
            timeout=timezone.now() + timeout,
            start_byte=start,
            end_byte=chunk - 1,
            total_size=len(content),
        )

        string_file = BytesIO(content[start:chunk])
        django_file = files.File(string_file)
        staged_file.file.save(f"{client_filename}_{uuid.uuid4()}", django_file)

        staged_file.save()

        assert staged_file.file.size == chunk - start

        start = chunk + 1

    return new_uuid


@pytest.mark.django_db
def test_uploaded_file_assembly():
    file_content = b"HelloWorld" * 5
    uploaded_file_uuid = create_uploaded_file(
        file_content,
        [len(file_content)],
        client_filename="bla")

    testee = StagedAjaxFile(uploaded_file_uuid)

    assert testee.exists
    assert testee.is_complete
    assert testee.name == "bla"
    assert testee.size == len(file_content)

    with testee.open() as file:
        l = len("HelloWorld")
        assert file.read(l) == b"HelloWorld"
        assert file.read(l) == b"HelloWorld"

        assert file.seek(0) == file.tell()
        assert file.read() == file_content


@pytest.mark.django_db
def test_file_cleanup():
    file_content = b"HelloWorld" * 5
    uploaded_file_uuid = create_uploaded_file(
        file_content,
        [len(file_content)],
        client_filename="bla",
        timeout=timedelta(milliseconds=100))

    testee = StagedAjaxFile(uploaded_file_uuid)

    assert testee.exists
    chunks = StagedFile.objects.filter(file_id=testee.uuid).all()
    assert len(chunks) > 0

    # Force timeout and clean
    now = timezone.now()
    for chunk in chunks:
        chunk.timeout = now - timedelta(hours=1)
        chunk.save()
    cleanup_stale_files()

    assert not testee.exists

    chunks = StagedFile.objects.filter(file_id=testee.uuid).all()
    assert len(chunks) == 0
