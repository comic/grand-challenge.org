import io
import os
import tarfile
from contextlib import contextmanager

from django.core.files import File
from docker.api.container import ContainerApiMixin


@contextmanager
def cleanup(container: ContainerApiMixin):
    """
    Cleans up a docker container which is running in detached mode

    :param container: An instance of a container
    :return:
    """
    try:
        yield container

    finally:
        container.stop()
        container.remove(force=True)


def put_file(*, container: ContainerApiMixin, src: File, dest: str) -> ():
    """
    Puts a file on the host into a container.
    This method will create an in memory tar archive, add the src file to this
    and upload it to the docker container where it will be unarchived at dest.

    :param container: The container to write to
    :param src: The path to the source file on the host
    :param dest: The path to the target file in the container
    :return:
    """
    tar_b = io.BytesIO()

    tarinfo = tarfile.TarInfo(name=os.path.basename(dest))
    tarinfo.size = src.size

    with tarfile.open(fileobj=tar_b, mode='w') as tar, src.open('rb') as f:
        tar.addfile(tarinfo, fileobj=f)

    tar_b.seek(0)
    container.put_archive(os.path.dirname(dest), tar_b)
