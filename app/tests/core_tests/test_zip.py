import pytest
from django.core.exceptions import SuspiciousFileOperation

from grandchallenge.core.utils.zip import zip_memory_buffer


def test_zip_memory_buffer_illigal_sym_link(tmp_path):

    allowed_base = tmp_path / "allowed_base"
    allowed_base.mkdir()

    file_path = (
        tmp_path / "test_file.txt"  # Note: next to and not under allowed base
    )
    file_path.write_text("This is a test file.")

    symlink_path = allowed_base / "symlink_to_test_file.txt"
    symlink_path.symlink_to(file_path)

    with pytest.raises(SuspiciousFileOperation):
        zip_memory_buffer(source=allowed_base)


def test_zip_memory_buffer_legal_sym_link(tmp_path):

    allowed_base = tmp_path / "allowed_base"
    allowed_base.mkdir()

    file_path = allowed_base / "test_file.txt"  # Note: under allowed base
    file_path.write_text("This is a test file.")

    symlink_path = allowed_base / "symlink_to_test_file.txt"
    symlink_path.symlink_to(file_path)

    zip_memory_buffer(source=allowed_base)
