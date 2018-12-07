from uuid import UUID

import numpy as np
import pytest
from PIL import Image as PILImage

from grandchallenge.retina_images.models import RetinaImage
from tests.retina_images_tests.factories import RetinaImageFactory
from tests.retina_core_tests.factories import create_oct_series
from tests.model_helpers import batch_test_factories

@pytest.mark.django_db
class TestRetinaImagesModels:
    # test functions are added dynamically to this class
    def test_retina_image_str(self):
        model = RetinaImageFactory()
        assert str(model) == "<{} {} {}>".format(model.__class__.__name__, model.name, model.modality)


factories = {
    "image": RetinaImageFactory,
}
batch_test_factories(factories, TestRetinaImagesModels)


@pytest.mark.django_db
class TestImage:
    def test_create_image_file_name(self):
        # create test image
        retina_image = RetinaImageFactory()
        filename = RetinaImage.create_image_file_name(retina_image.image)
        name, ext = filename.split(".")

        try:
            UUID(name, version=4)
        except ValueError:
            pytest.fail("Filename does not contain valid uuidv4")

        assert ext == "jpg"

    def test_get_all_oct_images(self):
        series_oct, images_oct = create_oct_series()
        all_images_qs = images_oct[0].get_all_oct_images()

        # Check if images_oct and all_images contain the same models
        all_images = [x for x in all_images_qs] # Convert Queryset to list
        for img in images_oct:
            if img in all_images:
                # remove from list
                all_images.remove(img)
            else:
                pytest.fail("{} not in list of OCT images")
                break

        assert len(all_images) == 0

    def test_get_all_oct_images_wrong_modality(self):
        all_images = RetinaImageFactory(modality=RetinaImage.MODALITY_CF).get_all_oct_images()
        assert all_images == []

    def test_get_all_oct_images_as_npy(self):
        series_oct, images_oct = create_oct_series()
        npy = images_oct[0].get_all_oct_images_as_npy()
        for index, npy_image in enumerate(npy):
            assert np.array_equal(
                npy_image, np.array(PILImage.open(images_oct[index].image.path))
            )