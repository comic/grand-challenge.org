import pytest
import factory
from pathlib import Path
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.conf import settings
from tests.factories import ImageFileFactory
from tests.cases_tests.factories import (
    ImageFactory,
    ImageFactoryWithImageFile,
    ImageFileFactoryWithMHDFile,
    ImageFileFactoryWithRAWFile,
)
from tests.model_helpers import batch_test_factories


@pytest.mark.django_db
class TestRetinaImagesModels:
    # test functions are added dynamically to this class
    def test_retina_image_str(self):
        model = ImageFactory()
        assert str(model) == f"Image {model.name} {model.shape_without_color}"


factories = {"image": ImageFactory}
batch_test_factories(factories, TestRetinaImagesModels)


@pytest.mark.django_db
class TestGetSitkImage:
    def test_multiple_mhds(self):
        extra_mhd = ImageFileFactoryWithMHDFile()
        extra_mhd_file = ImageFileFactoryWithMHDFile()
        extra_raw = ImageFileFactoryWithRAWFile()
        extra_raw_file = ImageFileFactoryWithRAWFile()
        image = ImageFactoryWithImageFile(
            files=(extra_mhd, extra_raw, extra_mhd_file, extra_raw_file)
        )
        try:
            image.get_sitk_image()
            pytest.fail("No MultipleObjectsReturned exception")
        except MultipleObjectsReturned:
            pass

    def test_no_mhd_object(self):
        image = ImageFactoryWithImageFile()
        image.files.get(file__endswith=".mhd").delete()
        try:
            image.get_sitk_image()
            pytest.fail("No ObjectDoesNotExist exception for mhd object")
        except ObjectDoesNotExist:
            pass

    def test_no_raw_object(self):
        image = ImageFactoryWithImageFile()
        image.files.get(file__endswith=".zraw").delete()
        try:
            image.get_sitk_image()
            pytest.fail("No ObjectDoesNotExist exception")
        except ObjectDoesNotExist:
            pass

    def test_file_not_found_mhd(self):
        image = ImageFactoryWithImageFile()
        imagefile = image.files.get(file__endswith=".mhd")
        imagefile.file.storage.delete(imagefile.file.name)
        try:
            image.get_sitk_image()
            pytest.fail("No FileNotFoundError exception")
        except FileNotFoundError:
            pass

    def test_file_not_found_raw(self):
        image = ImageFactoryWithImageFile()
        imagefile = image.files.get(file__endswith=".zraw")
        imagefile.file.storage.delete(imagefile.file.name)
        try:
            image.get_sitk_image()
            pytest.fail("No FileNotFoundError exception")
        except FileNotFoundError:
            pass

    def test_file_too_large_throws_error(self, tmpdir):
        image = ImageFactoryWithImageFile()

        # Remove zraw file
        old_raw = image.files.get(file__endswith=".zraw")
        raw_file_name = Path(old_raw.file.name).name
        old_raw.delete()

        # Create fake too large zraw file
        too_large_file_raw = tmpdir.join(raw_file_name)
        f = too_large_file_raw.open(mode="wb")
        f.seek(settings.MAX_SITK_FILE_SIZE)
        f.write(b"\0")
        f.close()

        # Add too large file as ImageFile model to image.files
        too_large_file_field = factory.django.FileField(
            from_path=str(too_large_file_raw)
        )
        too_large_imagefile = ImageFileFactory(file=too_large_file_field)
        image.files.add(too_large_imagefile)

        # Try to open and catch expected exception
        try:
            image.get_sitk_image()
            pytest.fail("No File exceeds maximum exception")
        except IOError as e:
            assert "File exceeds maximum file size." in str(e)

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
