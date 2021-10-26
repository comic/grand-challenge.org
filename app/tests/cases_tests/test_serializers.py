import pytest

from grandchallenge.cases.serializers import HyperlinkedImageSerializer
from grandchallenge.retina_api.serializers import RetinaImageSerializer
from tests.annotations_tests.factories import (
    LandmarkAnnotationSetFactory,
    SingleLandmarkAnnotationFactory,
)
from tests.cases_tests.factories import ImageFactoryWithImageFile
from tests.factories import ImageFactory, UserFactory
from tests.serializer_helpers import (
    check_if_valid,
    do_test_serializer_fields,
    do_test_serializer_valid,
)


@pytest.mark.django_db
class TestRetinaImageSerializers:
    def test_image_serializer_valid(self):
        assert check_if_valid(
            ImageFactoryWithImageFile(), RetinaImageSerializer
        )

    def test_landmarks_empty(self):
        i1 = ImageFactory()
        landmarks = RetinaImageSerializer(i1).data["landmark_annotations"]
        assert len(landmarks) == 0

    def test_landmarks_single(self):
        u = UserFactory()
        i1 = ImageFactory()
        i2 = ImageFactory()
        las = LandmarkAnnotationSetFactory(grader=u)
        SingleLandmarkAnnotationFactory(annotation_set=las, image=i1)
        SingleLandmarkAnnotationFactory(annotation_set=las, image=i2)
        landmarks = RetinaImageSerializer(i1).data["landmark_annotations"]
        assert len(landmarks) == 1
        assert landmarks == [i2.pk]

    def test_landmarks_multiple(self):
        u = UserFactory()
        i1 = ImageFactory()
        img_pks = set()
        for _ in range(4):
            img = ImageFactory()
            las = LandmarkAnnotationSetFactory(grader=u)
            SingleLandmarkAnnotationFactory(annotation_set=las, image=img)
            SingleLandmarkAnnotationFactory(annotation_set=las, image=i1)
            img_pks.add(img.pk)
        landmarks = RetinaImageSerializer(i1).data["landmark_annotations"]
        assert len(landmarks) == 4
        assert set(landmarks) == img_pks


@pytest.mark.django_db
@pytest.mark.parametrize(
    "serializer_data",
    (
        (
            {
                "unique": True,
                "factory": ImageFactoryWithImageFile,
                "serializer": HyperlinkedImageSerializer,
                "fields": (
                    "pk",
                    "name",
                    "files",
                    "width",
                    "height",
                    "depth",
                    "color_space",
                    "modality",
                    "eye_choice",
                    "stereoscopic_choice",
                    "field_of_view",
                    "shape_without_color",
                    "shape",
                    "voxel_width_mm",
                    "voxel_height_mm",
                    "voxel_depth_mm",
                    "api_url",
                    "patient_id",
                    "patient_name",
                    "patient_birth_date",
                    "patient_age",
                    "patient_sex",
                    "study_date",
                    "study_instance_uid",
                    "series_instance_uid",
                    "study_description",
                    "series_description",
                ),
                "no_valid_check": True,
                # This check is done manually because of the need to skip the image in the check
            },
        )
    ),
)
class TestSerializers:
    def test_serializer_valid(self, serializer_data):
        do_test_serializer_valid(serializer_data)

    def test_serializer_fields(self, serializer_data):
        do_test_serializer_fields(serializer_data)
