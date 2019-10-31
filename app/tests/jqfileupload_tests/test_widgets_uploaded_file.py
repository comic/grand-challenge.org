import uuid
from datetime import timedelta
from io import BytesIO

import pytest
from django.core import files
from django.utils import timezone

from grandchallenge.core.storage import private_s3_storage
from grandchallenge.jqfileupload.models import StagedFile
from grandchallenge.jqfileupload.widgets.uploader import (
    NotFoundError,
    StagedAjaxFile,
    cleanup_stale_files,
)


def create_uploaded_file(
    content: bytes,
    chunks=None,
    user_pk_str="test_user_pk",
    client_id="test_client_id",
    client_filename="test_client_filename_{uuid}",
    timeout=None,
    init_total_size=True,
) -> uuid.UUID:
    if chunks is None:
        chunks = [len(content)]

    if timeout is None:
        timeout = timedelta(minutes=1)

    new_uuid = uuid.uuid4()
    client_filename = client_filename.format(uuid=new_uuid)
    start = 0
    if type(init_total_size) == int:
        total_size = init_total_size
    elif init_total_size:
        total_size = len(content)
    else:
        total_size = None
    for chunk in chunks:
        staged_file = StagedFile(
            user_pk_str=user_pk_str,
            client_id=client_id,
            client_filename=client_filename,
            file_id=new_uuid,
            timeout=timezone.now() + timeout,
            start_byte=start,
            end_byte=chunk - 1,
            total_size=total_size,
        )
        string_file = BytesIO(content[start:chunk])
        django_file = files.File(string_file)
        staged_file.file.save(f"{client_filename}_{uuid.uuid4()}", django_file)
        staged_file.save()
        assert staged_file.file.size == chunk - start
        start = chunk
    return new_uuid


def do_default_content_tests(uploaded_file, file_content):
    test_len = 10
    assert uploaded_file.exists
    assert uploaded_file.is_complete
    assert uploaded_file.size == len(file_content)
    with uploaded_file.open() as file:
        assert file.read(test_len) == file_content[0:test_len]
        assert file.read(test_len) == file_content[test_len : 2 * test_len]
        assert file.seek(0) == file.tell()
        assert file.read() == file_content
        assert file.seek(-1, 1) == len(file_content) - 1
        assert file.seek(-2, 2) == len(file_content) - 2
        assert file.read(10) == file_content[-2:]
        assert file.read(10) == b""
        # Test if the correct names argument is used
        assert file.read(size=10) == b""
        # Test all read methods
        file.seek(0)
        assert file.read(-12) == file_content
        file.seek(0)
        assert file.read(test_len) == file_content[0:test_len]
        file.seek(0)
        assert file.read1(test_len) == file_content[0:test_len]
        byte_buffer = bytearray(b"0" * test_len)
        file.seek(0)
        assert file.readinto(byte_buffer) == test_len
        assert byte_buffer == file_content[0:test_len]
        file.seek(len(file_content) + 10)
        assert file.readinto(byte_buffer) == 0
        assert byte_buffer == file_content[0:test_len]
        byte_buffer = bytearray(b"0" * test_len)
        file.seek(0)
        assert file.readinto1(byte_buffer) == test_len
        assert byte_buffer == file_content[0:test_len]
        file.seek(len(file_content) + 10)
        assert file.readinto1(byte_buffer) == 0
        assert byte_buffer == file_content[0:test_len]
        assert file.readable()
        assert not file.writable()
        assert file.seekable()
        with pytest.raises(IOError):
            file.seek(-100)
        file.seek(len(file_content) + 100)
        assert file.read(10) == b""
        file.close()
        with pytest.raises(ValueError):
            file.read()
        with pytest.raises(ValueError):
            file.seek(0)
        with pytest.raises(ValueError):
            file.tell()
        assert file.size is None
        assert file.closed


def test_invalid_initialization():
    with pytest.raises(TypeError):
        StagedAjaxFile("blablalbal")


@pytest.mark.django_db
def test_staged_file_to_django_file():
    file_content = b"HelloWorld" * 5
    uploaded_file_uuid = create_uploaded_file(
        file_content, client_filename="bla"
    )
    tested_file = StagedAjaxFile(uploaded_file_uuid)
    assert tested_file.name == "bla"
    with tested_file.open() as f:
        djangofile = files.File(f)
        assert djangofile.read() == file_content
        assert djangofile.read(1) == b""


@pytest.mark.django_db
def test_uploaded_single_chunk_file():
    file_content = b"HelloWorld" * 5
    uploaded_file_uuid = create_uploaded_file(
        file_content, client_filename="bla"
    )
    tested_file = StagedAjaxFile(uploaded_file_uuid)
    assert tested_file.name == "bla"
    assert StagedFile.objects.filter(file_id=tested_file.uuid).count() == 1
    do_default_content_tests(tested_file, file_content)


@pytest.mark.django_db
def test_uploaded_multi_chunk_file():
    file_content = b"HelloWorld" * 5
    uploaded_file_uuid = create_uploaded_file(
        file_content,
        chunks=[4, 8, 10, 11, len(file_content)],
        client_filename="splittered",
    )
    tested_file = StagedAjaxFile(uploaded_file_uuid)
    assert tested_file.name == "splittered"
    assert StagedFile.objects.filter(file_id=tested_file.uuid).count() == 5
    do_default_content_tests(tested_file, file_content)


@pytest.mark.django_db
def test_file_cleanup():
    file_content = b"HelloWorld" * 5
    uploaded_file_uuid = create_uploaded_file(
        file_content,
        [len(file_content)],
        client_filename="bla",
        timeout=timedelta(milliseconds=100),
    )
    tested_file = StagedAjaxFile(uploaded_file_uuid)
    assert tested_file.exists
    chunks = StagedFile.objects.filter(file_id=tested_file.uuid).all()
    assert len(chunks) > 0

    for chunk in chunks:
        assert private_s3_storage.exists(name=chunk.file.name)

    # Force timeout and clean
    now = timezone.now()
    for chunk in chunks:
        chunk.timeout = now - timedelta(hours=1)
        chunk.save()

    cleanup_stale_files()

    assert not tested_file.exists
    assert len(StagedFile.objects.filter(file_id=tested_file.uuid).all()) == 0

    for chunk in chunks:
        assert not private_s3_storage.exists(name=chunk.file.name)


@pytest.mark.django_db
def test_missing_file():
    file_content = b"HelloWorld" * 5
    uploaded_file_uuid = create_uploaded_file(
        file_content, [len(file_content)]
    )
    tested_file = StagedAjaxFile(uploaded_file_uuid)
    assert tested_file.exists
    assert tested_file.is_complete
    chunks = StagedFile.objects.filter(file_id=tested_file.uuid).all()
    chunks.delete()
    assert not tested_file.exists
    assert not tested_file.is_complete
    with pytest.raises(NotFoundError):
        tested_file.name
    with pytest.raises(NotFoundError):
        tested_file.size
    with pytest.raises(NotFoundError):
        tested_file.delete()
    with pytest.raises(IOError):
        tested_file.open()


@pytest.mark.django_db
def test_file_missing_chunk():
    file_content = b"HelloWorld" * 5
    uploaded_file_uuid = create_uploaded_file(
        file_content, list(range(1, len(file_content) + 1))
    )
    tested_file = StagedAjaxFile(uploaded_file_uuid)
    assert tested_file.exists
    assert tested_file.is_complete
    assert tested_file.size == len(file_content)
    # delete chunk
    chunks = StagedFile.objects.filter(file_id=uploaded_file_uuid).all()
    chunks[4].delete()
    assert tested_file.exists
    assert not tested_file.is_complete
    assert tested_file.size is None


@pytest.mark.django_db
def test_file_missing_last_chunk():
    file_content = b"HelloWorld" * 5
    uploaded_file_uuid = create_uploaded_file(
        file_content, list(range(1, len(file_content) + 1))
    )
    tested_file = StagedAjaxFile(uploaded_file_uuid)
    assert tested_file.exists
    assert tested_file.is_complete
    assert tested_file.size == len(file_content)
    # delete chunk
    chunks = StagedFile.objects.filter(file_id=uploaded_file_uuid).all()
    chunks[len(chunks) - 1].delete()
    assert tested_file.exists
    assert not tested_file.is_complete
    assert tested_file.size is None


@pytest.mark.django_db
def test_file_overlapping_chunk():
    file_content = b"HelloWorld" * 5
    uploaded_file_uuid = create_uploaded_file(
        file_content, list(range(1, len(file_content) + 1))
    )
    tested_file = StagedAjaxFile(uploaded_file_uuid)
    chunks = StagedFile.objects.filter(file_id=uploaded_file_uuid).all()
    chunk4 = chunks[4]
    chunk4.pk = None
    chunk4.start_byte = 0
    chunk4.end_byte = 10
    chunk4.save()
    assert tested_file.exists
    assert not tested_file.is_complete
    assert tested_file.size is None


@pytest.mark.django_db
def test_file_no_total_size():
    file_content = b"HelloWorld" * 5
    uploaded_file_uuid = create_uploaded_file(
        file_content,
        list(range(1, len(file_content) + 1)),
        init_total_size=False,
    )
    tested_file = StagedAjaxFile(uploaded_file_uuid)
    assert tested_file.exists
    assert tested_file.is_complete
    assert tested_file.size == len(file_content)
    chunks = StagedFile.objects.filter(file_id=uploaded_file_uuid).all()
    chunks[4].delete()
    assert tested_file.exists
    assert not tested_file.is_complete
    assert tested_file.size is None


@pytest.mark.django_db
def test_file_deletion():
    file_content = b"HelloWorld" * 5
    uploaded_file_uuid = create_uploaded_file(
        file_content,
        list(range(1, len(file_content) + 1)),
        init_total_size=False,
    )
    tested_file = StagedAjaxFile(uploaded_file_uuid)
    assert tested_file.exists
    assert tested_file.is_complete
    assert tested_file.size == len(file_content)
    chunks = StagedFile.objects.filter(file_id=uploaded_file_uuid).all()
    file_paths = [chunk.file.name for chunk in chunks]
    for path in file_paths:
        assert private_s3_storage.exists(path)
    tested_file.delete()
    assert not tested_file.exists
    assert not tested_file.is_complete
    for path in file_paths:
        assert not private_s3_storage.exists(path)
