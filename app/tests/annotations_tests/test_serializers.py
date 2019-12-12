import pytest

from grandchallenge.annotations.serializers import (
    BooleanClassificationAnnotationSerializer,
    ETDRSGridAnnotationSerializer,
    ImagePathologyAnnotationSerializer,
    ImageQualityAnnotationSerializer,
    ImageTextAnnotationSerializer,
    LandmarkAnnotationSetSerializer,
    MeasurementAnnotationSerializer,
    PolygonAnnotationSetSerializer,
    RetinaImagePathologyAnnotationSerializer,
    SingleLandmarkAnnotationSerializer,
    SingleLandmarkAnnotationSerializerNoParent,
    SinglePolygonAnnotationSerializer,
)
from tests.annotations_tests.factories import (
    BooleanClassificationAnnotationFactory,
    ETDRSGridAnnotationFactory,
    ImagePathologyAnnotationFactory,
    ImageQualityAnnotationFactory,
    ImageTextAnnotationFactory,
    LandmarkAnnotationSetFactory,
    MeasurementAnnotationFactory,
    PolygonAnnotationSetFactory,
    RetinaImagePathologyAnnotationFactory,
    SingleLandmarkAnnotationFactory,
    SinglePolygonAnnotationFactory,
)
from tests.factories import ImageFactory, UserFactory
from tests.serializer_helpers import (
    do_test_serializer_fields,
    do_test_serializer_valid,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "serializer_data",
    (
        (
            {
                "unique": True,
                "factory": ETDRSGridAnnotationFactory,
                "serializer": ETDRSGridAnnotationSerializer,
                "fields": (
                    "id",
                    "grader",
                    "created",
                    "image",
                    "fovea",
                    "optic_disk",
                ),
            },
            {
                "unique": True,
                "factory": MeasurementAnnotationFactory,
                "serializer": MeasurementAnnotationSerializer,
                "fields": (
                    "image",
                    "grader",
                    "created",
                    "start_voxel",
                    "end_voxel",
                ),
            },
            {
                "unique": True,
                "factory": BooleanClassificationAnnotationFactory,
                "serializer": BooleanClassificationAnnotationSerializer,
                "fields": ("image", "grader", "created", "name", "value"),
            },
            {
                "unique": True,
                "factory": PolygonAnnotationSetFactory,
                "serializer": PolygonAnnotationSetSerializer,
                "fields": (
                    "id",
                    "image",
                    "grader",
                    "created",
                    "name",
                    "singlepolygonannotation_set",
                ),
            },
            {
                "unique": True,
                "factory": SinglePolygonAnnotationFactory,
                "serializer": SinglePolygonAnnotationSerializer,
                "fields": (
                    "id",
                    "value",
                    "annotation_set",
                    "created",
                    "x_axis_orientation",
                    "y_axis_orientation",
                    "z",
                ),
            },
            {
                "unique": True,
                "factory": LandmarkAnnotationSetFactory,
                "serializer": LandmarkAnnotationSetSerializer,
                "fields": (
                    "id",
                    "grader",
                    "created",
                    "singlelandmarkannotation_set",
                ),
            },
            {
                "unique": True,
                "factory": SingleLandmarkAnnotationFactory,
                "serializer": SingleLandmarkAnnotationSerializer,
                "fields": ("id", "image", "annotation_set", "landmarks"),
            },
            {
                "unique": True,
                "factory": SingleLandmarkAnnotationFactory,
                "serializer": SingleLandmarkAnnotationSerializerNoParent,
                "fields": ("id", "image", "landmarks"),
            },
            {
                "unique": True,
                "factory": ImageQualityAnnotationFactory,
                "serializer": ImageQualityAnnotationSerializer,
                "fields": (
                    "id",
                    "created",
                    "grader",
                    "image",
                    "quality",
                    "quality_reason",
                ),
            },
            {
                "unique": True,
                "factory": ImagePathologyAnnotationFactory,
                "serializer": ImagePathologyAnnotationSerializer,
                "fields": ("id", "created", "grader", "image", "pathology"),
            },
            {
                "unique": True,
                "factory": RetinaImagePathologyAnnotationFactory,
                "serializer": RetinaImagePathologyAnnotationSerializer,
                "fields": (
                    "id",
                    "grader",
                    "created",
                    "image",
                    "amd_present",
                    "dr_present",
                    "oda_present",
                    "myopia_present",
                    "cysts_present",
                    "other_present",
                ),
            },
            {
                "unique": True,
                "factory": ImageTextAnnotationFactory,
                "serializer": ImageTextAnnotationSerializer,
                "fields": ("id", "grader", "created", "image", "text"),
            },
        )
    ),
)
class TestSerializers:
    def test_serializer_valid(self, serializer_data):
        do_test_serializer_valid(serializer_data)

    def test_serializer_fields(self, serializer_data):
        do_test_serializer_fields(serializer_data)


@pytest.mark.django_db
class TestNestedLandmarkSerializer:
    def test_serialization(self, multiple_landmark_annotation_sets):
        serialized_model = LandmarkAnnotationSetSerializer(
            instance=multiple_landmark_annotation_sets.landmarkset1
        )
        assert serialized_model.data.get("id") is not None
        assert serialized_model.data.get("created") is not None
        assert (
            serialized_model.data.get("grader")
            == multiple_landmark_annotation_sets.grader1.id
        )
        assert (
            len(serialized_model.data.get("singlelandmarkannotation_set")) == 2
        )
        assert (
            serialized_model.data["singlelandmarkannotation_set"][0].get("id")
            is not None
        )
        assert (
            serialized_model.data["singlelandmarkannotation_set"][0].get(
                "image"
            )
            is not None
        )
        assert (
            serialized_model.data["singlelandmarkannotation_set"][0].get(
                "landmarks"
            )
            is not None
        )
        assert (
            len(
                serialized_model.data["singlelandmarkannotation_set"][0][
                    "landmarks"
                ]
            )
            > 0
        )
        assert (
            len(
                serialized_model.data["singlelandmarkannotation_set"][0][
                    "landmarks"
                ][0]
            )
            == 2
        )

    @staticmethod
    def create_annotation_set():
        user = UserFactory()
        image1 = ImageFactory()
        image2 = ImageFactory()
        return {
            "grader": user.id,
            "singlelandmarkannotation_set": [
                {"image": image1.id, "landmarks": [[0, 0], [1, 1], [2, 2]]},
                {"image": image2.id, "landmarks": [[1, 1], [2, 2], [3, 3]]},
            ],
        }

    def save_annotation_set(self):
        annotation_set_dict = self.create_annotation_set()
        serializer = LandmarkAnnotationSetSerializer(data=annotation_set_dict)
        serializer.is_valid()
        annotation_set_obj = serializer.save()
        return annotation_set_dict, annotation_set_obj

    def test_create_method(self):
        annotation_set = self.create_annotation_set()
        serializer = LandmarkAnnotationSetSerializer(data=annotation_set)
        serializer.is_valid()
        assert serializer.errors == {}
        try:
            obj = serializer.save()
            assert obj.singlelandmarkannotation_set.count() == 2
        except Exception as e:
            pytest.fail(f"Saving serializer failed with error: {str(e)}")

    def test_update_method_instance_fields_do_not_change(self):
        annotation_set_dict, annotation_set_obj = self.save_annotation_set()
        other_user = UserFactory()
        updated_set = {
            **annotation_set_dict,
            "id": annotation_set_obj.id,
            "grader": other_user.id,
        }
        serializer = LandmarkAnnotationSetSerializer(
            annotation_set_obj, data=updated_set
        )
        serializer.is_valid()
        saved_set = None
        try:
            saved_set = serializer.save()
        except Exception as e:
            pytest.fail(f"Saving serializer failed with error: {str(e)}")
        assert saved_set.grader == annotation_set_obj.grader

    def test_update_method_new_slas_get_added_existing_get_updated(self):
        annotation_set_dict, annotation_set_obj = self.save_annotation_set()
        old_slas = list(annotation_set_obj.singlelandmarkannotation_set.all())
        image3 = ImageFactory()
        new_slas = [
            {"image": image3.id, "landmarks": [[2, 2], [3, 3], [4, 4]]},
            {
                "image": old_slas[0].image.id,
                "landmarks": [[4, 4], [5, 5], [6, 6]],
            },
        ]
        updated_set = {
            **annotation_set_dict,
            "singlelandmarkannotation_set": new_slas,
        }
        serializer = LandmarkAnnotationSetSerializer(
            annotation_set_obj, data=updated_set
        )
        serializer.is_valid()
        saved_set = None
        try:
            saved_set = serializer.save()
        except Exception as e:
            pytest.fail(f"Saving serializer failed with error: {str(e)}")
        assert saved_set.singlelandmarkannotation_set.count() == 3
        assert saved_set.singlelandmarkannotation_set.filter(
            image=image3
        ).exists()
        assert saved_set.singlelandmarkannotation_set.get(
            image__id=old_slas[0].image.id
        ).landmarks == [[4.0, 4.0], [5.0, 5.0], [6.0, 6.0]]

    def test_update_method_removes_empty_sla(self):
        annotation_set_dict, annotation_set_obj = self.save_annotation_set()
        old_slas = list(annotation_set_obj.singlelandmarkannotation_set.all())
        new_slas = [{"image": old_slas[0].image.id, "landmarks": []}]
        updated_set = {
            **annotation_set_dict,
            "singlelandmarkannotation_set": new_slas,
        }
        serializer = LandmarkAnnotationSetSerializer(
            annotation_set_obj, data=updated_set
        )
        serializer.is_valid()
        saved_set = None
        try:
            saved_set = serializer.save()
        except Exception as e:
            pytest.fail(f"Saving serializer failed with error: {str(e)}")
        assert saved_set.singlelandmarkannotation_set.count() == 1
        assert not saved_set.singlelandmarkannotation_set.filter(
            image=old_slas[0].image.id
        ).exists()
