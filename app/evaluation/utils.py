import io
import os
import tarfile

from django.core.files import File
from docker.api.container import ContainerApiMixin


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
    tar = tarfile.open(fileobj=tar_b, mode='w')
    tarinfo = tarfile.TarInfo(name=os.path.basename(dest))
    tarinfo.size = src.size

    # type File does not have a __enter__ method, so cannot use `with`
    src.open('rb')
    try:
        tar.addfile(tarinfo, fileobj=src)
    finally:
        src.close()
        tar.close()

    tar_b.seek(0)
    container.put_archive(os.path.dirname(dest), tar_b)
