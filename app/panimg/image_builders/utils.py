from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import AnyStr, Optional, Sequence, Tuple
from uuid import uuid4

import SimpleITK

from panimg.models import ColorSpace, ImageType, PanImg, PanImgFile
from panimg.settings import ITK_INTERNAL_FILE_FORMAT


def convert_itk_to_internal(
    *,
    simple_itk_image: SimpleITK.Image,
    output_directory: Path,
    name: Optional[AnyStr] = None,
    use_spacing: Optional[bool] = True,
) -> Tuple[PanImg, Sequence[PanImgFile]]:
    color_space = simple_itk_image.GetNumberOfComponentsPerPixel()
    color_space = {
        1: ColorSpace.GRAY,
        3: ColorSpace.RGB,
        4: ColorSpace.RGBA,
    }.get(color_space, None)
    if color_space is None:
        raise ValueError("Unknown color space for MetaIO image.")

    with TemporaryDirectory() as work_dir:
        work_dir = Path(work_dir)

        pk = uuid4()
        if not name:
            name = str(pk)
        SimpleITK.WriteImage(
            simple_itk_image,
            str(work_dir / f"{pk}.{ITK_INTERNAL_FILE_FORMAT}"),
            True,
        )

        if simple_itk_image.GetDimension() == 4:
            timepoints = simple_itk_image.GetSize()[-1]
        else:
            timepoints = None
        depth = simple_itk_image.GetDepth()

        try:
            window_center = float(simple_itk_image.GetMetaData("WindowCenter"))
        except (RuntimeError, ValueError):
            window_center = None
        try:
            window_width = float(simple_itk_image.GetMetaData("WindowWidth"))
        except (RuntimeError, ValueError):
            window_width = None

        db_image = PanImg(
            pk=pk,
            name=name,
            width=simple_itk_image.GetWidth(),
            height=simple_itk_image.GetHeight(),
            depth=depth if depth else None,
            window_center=window_center,
            window_width=window_width,
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
            temp_file = NamedTemporaryFile(delete=False, dir=output_directory)
            with open(str(_file), "rb") as open_file:
                buffer = True
                while buffer:
                    buffer = open_file.read(1024)
                    temp_file.write(buffer)
            db_image_file = PanImgFile(
                image_id=db_image.pk,
                image_type=ImageType.MHD,
                file=Path(temp_file.name),
                filename=_file.name,
            )
            db_image_files.append(db_image_file)

    return db_image, db_image_files
