import os
from io import BytesIO, StringIO

from django.core.files import File
from django.core.files.storage import FileSystemStorage


def fake_file(filename, content="mock content"):
    """
    For testing I sometimes want specific file request to return
    specific content. This is to make creation easier
    """
    return {"filename": filename, "content": content}


class MockStorage(FileSystemStorage):
    """A storage class which does not write anything to disk."""

    # For testing, any dir in FAKE DIRS will exist and contain FAKE_FILES
    FAKE_DIRS = [
        "fake_test_dir",
    ]

    FAKE_FILES = [
        fake_file("fakefile1.txt"),
        fake_file("fakefile2.jpg"),
        fake_file("fakefile3.exe"),
        fake_file("fakefile4.mhd"),
        fake_file("fakecss.css", "body {width:300px;}"),
    ]

    def __init__(self):
        super(FileSystemStorage, self).__init__()
        self.saved_files = {}

    def _save(self, name, content):
        mockfile = File(content)
        mockfile.name = name
        self.saved_files[name] = mockfile
        return name

    def _open(self, path, mode="rb"):
        """
        Return a memory only file which will not be saved to disk.

        If an image is requested, fake image content using PIL.
        """
        if not self.exists(path):
            raise OSError(
                "Mockstorage: '%s' No such file or directory." % path
            )

        if path in self.saved_files.keys():
            return self.saved_files[path]

        if os.path.splitext(path)[1].lower() in [
            ".jpg",
            ".png",
            ".gif",
            ".bmp",
        ]:
            # 1px test image
            binary_image_data = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00"
                b"\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x01sRGB"
                b"\x00\xae\xce\x1c\xe9\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00"
                b"\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xdb"
                b"\x0c\x17\x020;\xd1\xda\xcf\xd2\x00\x00\x00\x0cIDAT\x08\xd7c"
                b"\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00"
                b"\x00IEND\xaeB`\x82"
            )
            img = BytesIO(binary_image_data)
            mockfile = File(img)
            mockfile.name = "MOCKED_IMAGE_" + path
        else:
            content = "mock content"
            # If a predefined fake file is asked for, return predefined content
            filename = os.path.split(path)[1]
            for content_name in self.FAKE_FILES:
                mockfilename = content_name["filename"]
                mockcontent = content_name["content"]
                if filename == mockfilename:
                    content = mockcontent
            mockfile = File(StringIO(content))
            mockfile.name = "MOCKED_FILE_" + path
        return mockfile

    def add_fake_file(self, filename, content):
        """Add a file in the ``/public_html`` folder."""
        self.FAKE_FILES.append(fake_file(filename, content))

    def delete(self, name):
        pass

    def exists(self, name):
        """
        Any file exists if one of the FAKE_DIRS are in its path. And its name
        is one of FAKE_FILES
        """
        if name in self.saved_files.keys():
            return True

        if name.endswith("/"):
            name = name[:-1]
        directory, file_or_folder = os.path.split(name)
        if "." in file_or_folder:  # input was a file path
            filenames = [x["filename"] for x in self.FAKE_FILES]
            return self.is_in_fake_test_dir(directory) and (
                file_or_folder in filenames
            )

        else:  # input was a directory path
            return self.is_in_fake_test_dir(directory)

    def listdir(self, path):
        if self.is_in_fake_test_dir(path):
            directories = []
            files = [x["filename"] for x in self.FAKE_FILES]
        else:
            if self.exists(path):
                directories, files = [], []
            else:
                # "This is what default storage would do when listing a non
                # existant dir "
                raise OSError("Directory does not exist")

        return directories, files

    def path(self, name):
        return name

    def size(self, name):
        filenames = [x["filename"] for x in self.FAKE_FILES]
        if self.is_in_fake_test_dir(name) & (
            os.path.split(name)[1] in filenames
        ):
            return 10000

        else:
            return 0

    def is_in_fake_test_dir(self, path):
        """
        Is this file in the special fake directory? This dir does not exist
        on disk but returns some values anyway. For testing.
        """
        for directory in self.FAKE_DIRS:
            if (
                directory in path
            ):  # very rough test. But this is only for testing
                return True

        return False
