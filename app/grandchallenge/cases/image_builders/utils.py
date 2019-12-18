from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile
from typing import AnyStr, Optional, Sequence, Tuple
from uuid import uuid4

import SimpleITK
from django.core.files import File

from grandchallenge.cases.models import Image, ImageFile


def convert_itk_to_internal(
    simple_itk_image: SimpleITK.Image,
    name: Optional[AnyStr] = None,
    use_spacing: Optional[bool] = True,
) -> Tuple[Image, Sequence[ImageFile]]:
    color_space = simple_itk_image.GetNumberOfComponentsPerPixel()
    color_space = {
        1: Image.COLOR_SPACE_GRAY,
        3: Image.COLOR_SPACE_RGB,
        4: Image.COLOR_SPACE_RGBA,
    }.get(color_space, None)
    if color_space is None:
        raise ValueError("Unknown color space for MetaIO image.")

    with TemporaryDirectory() as work_dir:
        work_dir = Path(work_dir)

        pk = uuid4()
        if not name:
            name = str(pk)
        SimpleITK.WriteImage(
            simple_itk_image, str(work_dir / f"{pk}.mhd"), True
        )

        if simple_itk_image.GetDimension() == 4:
            timepoints = simple_itk_image.GetSize()[-1]
        else:
            timepoints = None
        depth = simple_itk_image.GetDepth()
        db_image = Image(
            pk=pk,
            name=name,
            width=simple_itk_image.GetWidth(),
            height=simple_itk_image.GetHeight(),
            depth=depth if depth else None,
            timepoints=timepoints,
            resolution_levels=None,
            color_space=color_space,
            voxel_width_mm=simple_itk_image.GetSpacing()[0]
            if use_spacing
            else None,
            voxel_height_mm=simple_itk_image.GetSpacing()[1]
            if use_spacing
            else None,
            voxel_depth_mm=simple_itk_image.GetSpacing()[2] if depth else None,
        )
        db_image_files = []
        for _file in work_dir.iterdir():
            temp_file = TemporaryFile()
            with open(str(_file), "rb") as open_file:
                buffer = True
                while buffer:
                    buffer = open_file.read(1024)
                    temp_file.write(buffer)

            db_image_file = ImageFile(
                image=db_image,
                image_type=ImageFile.IMAGE_TYPE_MHD,
                file=File(temp_file, name=_file.name),
            )
            db_image_files.append(db_image_file)

    return db_image, db_image_files
