import pytest
from pathlib import Path
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

from tests.retina_images_tests.factories import ImageFactory, ImageFactoryWithImageFile, ImageFileFactoryWithMHDFile, ImageFileFactoryWithRAWFile
from tests.model_helpers import batch_test_factories

@pytest.mark.django_db
class TestRetinaImagesModels:
    # test functions are added dynamically to this class
    def test_retina_image_str(self):
        model = ImageFactory()
        assert str(model) == f"Image {model.name} {model.shape_without_color}"


factories = {
    "image": ImageFactory,
}
batch_test_factories(factories, TestRetinaImagesModels)


@pytest.mark.django_db
class TestGetSitkImage:
    def test_multiple_mhds(self):
        extra_mhd = ImageFileFactoryWithMHDFile()
        extra_mhd_file = ImageFileFactoryWithMHDFile()
        extra_raw = ImageFileFactoryWithRAWFile()
        extra_raw_file = ImageFileFactoryWithRAWFile()
        image = ImageFactoryWithImageFile(files=(extra_mhd, extra_raw, extra_mhd_file,extra_raw_file))
        try:
            image.get_sitk_image()
            pytest.fail("No MultipleObjectsReturned exception")
        except MultipleObjectsReturned:
            pass

    def test_no_mhds(self):
        image = ImageFactoryWithImageFile()
        image.files.all().delete()
        try:
            image.get_sitk_image()
            pytest.fail("No ObjectDoesNotExist exception")
        except ObjectDoesNotExist:
            pass

    def test_file_not_found(self):
        image = ImageFactoryWithImageFile()
        for file in image.files.all():
            Path.unlink(Path(file.file.path))
        try:
            image.get_sitk_image()
            pytest.fail("No FileNotFoundError exception")
        except FileNotFoundError:
            pass

    def test_no_raw_file(self):
        image = ImageFactoryWithImageFile()
        imagefile = image.files.get(file__endswith=".zraw")
        Path.unlink(Path(imagefile.file.path))
        try:
            image.get_sitk_image()
            pytest.fail("No exception with missing raw file")
        except RuntimeError as e:
            assert "Exception thrown in SimpleITK ReadImage:" in str(e)
            assert "File cannot be read" in str(e)
            assert "Reason: Success" in str(e)

    def test_correct_dimensions(self):
        image = ImageFactoryWithImageFile()
        sitk_image = image.get_sitk_image()
        assert sitk_image.GetDimension() == 3
        assert sitk_image.GetSize() == (7, 6, 5)
        assert sitk_image.GetOrigin() == (0.0, 0.0, 0.0)
        assert sitk_image.GetSpacing() == (1.0, 1.0, 1.0)
        assert sitk_image.GetNumberOfComponentsPerPixel() == 1
        assert sitk_image.GetPixelIDValue() == 0
        assert sitk_image.GetPixelIDTypeAsString() == "8-bit signed integer"

