from collections import namedtuple

ImageBuilderResult = namedtuple(
    "ImageBuilderResult",
    (
        "consumed_files",
        "file_errors_map",
        "new_images",
        "new_image_files",
        "new_folder_upload",
    ),
)
