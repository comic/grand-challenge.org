import uuid
from datetime import timedelta
from io import BytesIO

import pytest
from django.core import files
from django.utils import timezone

from jqfileupload.models import StagedFile
from jqfileupload.widgets.uploader import StagedAjaxFile, \
    cleanup_stale_files


def create_uploaded_file(
        content: str,
        chunks=None,
        csrf="test_csrf",
        client_id="test_client_id",
        client_filename="test_client_filename_{uuid}",
        timeout=timedelta(minutes=1)) -> uuid.UUID:
    if chunks is None:
        chunks = [len(content)]

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

        start = chunk

    return new_uuid


def do_default_content_tests(uploaded_file, file_content):
    l = 10

    assert uploaded_file.exists
    assert uploaded_file.is_complete
    assert uploaded_file.size == len(file_content)

    with uploaded_file.open() as file:
        assert file.read(l) == file_content[0:l]
        assert file.read(l) == file_content[l:2*l]

        assert file.seek(0) == file.tell()
        assert file.read() == file_content

        assert file.seek(-1, 1) == len(file_content) - 1
        assert file.seek(-2, 2) == len(file_content) - 2
        assert file.read(10) == file_content[-2:]

@pytest.mark.django_db
def test_uploaded_single_chunk_file():
    file_content = b"HelloWorld" * 5
    uploaded_file_uuid = create_uploaded_file(
        file_content,
        client_filename="bla")

    testee = StagedAjaxFile(uploaded_file_uuid)
    assert testee.name == "bla"

    assert StagedFile.objects.filter(file_id=testee.uuid).count() == 1

    do_default_content_tests(testee, file_content)

@pytest.mark.django_db
def test_uploaded_multi_chunk_file():
    file_content = b"HelloWorld" * 5
    uploaded_file_uuid = create_uploaded_file(
        file_content,
        chunks=[4, 8, 10, 11, len(file_content)],
        client_filename="splittered")

    testee = StagedAjaxFile(uploaded_file_uuid)
    assert testee.name == "splittered"

    assert StagedFile.objects.filter(file_id=testee.uuid).count() == 5

    do_default_content_tests(testee, file_content)

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
