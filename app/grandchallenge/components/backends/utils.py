import re
import zipfile
from os.path import commonpath
from pathlib import Path
from typing import List

from django.core.files import File
from django.utils._os import safe_join

LOGLINES = 2000  # The number of loglines to keep

# Docker logline error message with optional RFC3339 timestamp
LOGLINE_REGEX = r"^(?P<timestamp>([\d]+)-(0[1-9]|1[012])-(0[1-9]|[12][\d]|3[01])[Tt]([01][\d]|2[0-3]):([0-5][\d]):([0-5][\d]|60)(\.[\d]+)?(([Zz])|([\+|\-]([01][\d]|2[0-3]):[0-5][\d])))?(?P<error_message>.*)$"


def user_error(obj: str):
    """
    Filter an error message to just return the last, none-empty line. Used
    to return the last line of a traceback to a user.

    :param obj: A string with newlines
    :return: The last, none-empty line of obj
    """
    pattern = re.compile(LOGLINE_REGEX, re.MULTILINE)

    error_message = "No errors were reported in the logs."

    for m in re.finditer(pattern, obj):
        e = m.group("error_message").strip()
        if e:
            error_message = e

    return error_message


def safe_extract(*, src: File, dest: Path):
    """
    Safely extracts a zip file into a directory

    Any common prefixes and system files are removed.
    """

    if not dest.exists():
        raise RuntimeError("The destination must exist")

    with src.open() as f:
        with zipfile.ZipFile(f) as zf:
            members = _filter_members(zf.infolist())

            for member in members:
                file_dest = Path(safe_join(dest, member["dest"]))
                # We know that the dest is within the prefix as
                # safe_join is used, and the destination is already
                # created, so ok to create the parents here
                file_dest.parent.mkdir(exist_ok=True, parents=True)

                with zf.open(member["src"], "r") as fs, open(
                    file_dest, "wb"
                ) as fd:
                    while True:
                        chunk = fs.read(1024)
                        if not chunk:
                            break

                        fd.write(chunk)


def _filter_members(members: List[zipfile.ZipInfo]):
    """Filter common prefixes and uninteresting files from a zip archive"""
    members = [
        m.filename
        for m in members
        if not m.is_dir()
        and re.search(r"(__MACOSX|\.DS_Store|desktop.ini)", m.filename) is None
    ]

    # Remove any common parent directories
    if len(members) == 1:
        path = str(Path(members[0]).parent)
        path = "" if path == "." else path
    else:
        path = commonpath(members)

    if path:
        sliced_path = slice(len(path) + 1, None, None)
    else:
        sliced_path = slice(None, None, None)

    return [{"src": m, "dest": m[sliced_path]} for m in members]
