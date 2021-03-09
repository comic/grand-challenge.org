from panimg.image_builders.dicom import image_builder_dicom
from panimg.image_builders.fallback import image_builder_fallback
from panimg.image_builders.metaio_mhd_mha import image_builder_mhd
from panimg.image_builders.nifti import image_builder_nifti
from panimg.image_builders.tiff import image_builder_tiff

DEFAULT_IMAGE_BUILDERS = [
    image_builder_mhd,
    image_builder_nifti,
    image_builder_dicom,
    image_builder_tiff,
    image_builder_fallback,
]
