import copy
import json

import pytest
from guardian.shortcuts import assign_perm
from rest_framework import status
from rest_framework.test import force_authenticate

from grandchallenge.annotations.models import PolygonAnnotationSet
from grandchallenge.annotations.serializers import (
    BooleanClassificationAnnotationSerializer,
    ETDRSGridAnnotationSerializer,
    ImagePathologyAnnotationSerializer,
    ImageQualityAnnotationSerializer,
    ImageTextAnnotationSerializer,
    LandmarkAnnotationSetSerializer,
    NestedPolygonAnnotationSetSerializer,
    OctRetinaImagePathologyAnnotationSerializer,
    RetinaImagePathologyAnnotationSerializer,
    SinglePolygonAnnotationSerializer,
)
from grandchallenge.retina_api.views import (
    BooleanClassificationAnnotationViewSet,
    ETDRSGridAnnotationViewSet,
    ImageLevelAnnotationsForImageViewSet,
    LandmarkAnnotationSetViewSet,
    OctRetinaPathologyAnnotationViewSet,
    PathologyAnnotationViewSet,
    PolygonAnnotationSetViewSet,
    QualityAnnotationViewSet,
    RetinaImageViewSet,
    RetinaPathologyAnnotationViewSet,
    SinglePolygonViewSet,
    TextAnnotationViewSet,
)
from grandchallenge.subdomains.utils import reverse
from tests.annotations_tests.factories import (
    BooleanClassificationAnnotationFactory,
    ETDRSGridAnnotationFactory,
    ImagePathologyAnnotationFactory,
    ImageQualityAnnotationFactory,
    ImageTextAnnotationFactory,
    LandmarkAnnotationSetFactory,
    OctRetinaImagePathologyAnnotationFactory,
    PolygonAnnotationSetFactory,
    RetinaImagePathologyAnnotationFactory,
    SingleLandmarkAnnotationFactory,
    SinglePolygonAnnotationFactory,
)
from tests.cases_tests.factories import ImageFactory
from tests.conftest import add_to_graders_group
from tests.factories import UserFactory
from tests.viewset_helpers import get_user_from_user_type, view_test


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_type",
    [
        None,
        "normal_user",
        "retina_grader_non_allowed",
        "retina_grader",
        "retina_admin",
    ],
)
@pytest.mark.parametrize(
    "namespace,basename,viewset,serializer,with_user",
    [
        (
            "api",
            "retina-polygon-annotation-set",
            PolygonAnnotationSetViewSet,
            NestedPolygonAnnotationSetSerializer,
            False,
        ),
    ],
)
class TestPolygonAnnotationSetViewSet:
    def test_list_view(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        serializer,
        with_user,
    ):
        response = view_test(
            "list",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1,
            rf,
            viewset,
            with_user=with_user,
        )
        if user_type == "retina_grader":
            serialized_data = serializer(
                two_retina_polygon_annotation_sets.polygonset1
            ).data
            assert response.data == [serialized_data]
        if user_type == "retina_admin":
            serialized_data = serializer(
                [
                    two_retina_polygon_annotation_sets.polygonset1,
                    two_retina_polygon_annotation_sets.polygonset2,
                ],
                many=True,
            ).data
            serialized_data_sorted = sorted(
                serialized_data, key=lambda k: k["created"], reverse=True
            )
            assert response.data == serialized_data_sorted

    def test_create_view(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        serializer,
        with_user,
    ):
        model_build = PolygonAnnotationSetFactory.build()
        model_serialized = serializer(model_build).data
        image = ImageFactory()
        model_serialized["image"] = str(image.id)
        model_serialized[
            "grader"
        ] = two_retina_polygon_annotation_sets.grader1.id
        model_json = json.dumps(model_serialized)

        response = view_test(
            "create",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1,
            rf,
            viewset,
            model_json,
            with_user=with_user,
        )
        if user_type in ("retina_grader", "retina_admin"):
            model_serialized["id"] = response.data["id"]
            response.data["image"] = str(response.data["image"])
            assert response.data == model_serialized

    def test_create_view_wrong_user_id(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        serializer,
        with_user,
    ):
        model_build = PolygonAnnotationSetFactory.build()
        model_serialized = serializer(model_build).data
        image = ImageFactory()
        model_serialized["image"] = str(image.id)
        other_user = UserFactory()
        model_serialized["grader"] = other_user.id
        model_json = json.dumps(model_serialized)

        response = view_test(
            "create",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1,
            rf,
            viewset,
            model_json,
            with_user=with_user,
            check_response_status_code=False,
        )
        if user_type == "retina_admin":
            model_serialized["id"] = response.data["id"]
            response.data["image"] = str(response.data["image"])
            assert response.data == model_serialized
        elif user_type == "retina_grader":
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert (
                str(response.data["grader"][0])
                == "User is not allowed to create annotation for other grader"
            )
        else:
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_view(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        serializer,
        with_user,
    ):
        response = view_test(
            "retrieve",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1,
            rf,
            viewset,
            with_user=with_user,
        )
        if user_type == "retina_grader" or user_type == "retina_admin":
            model_serialized = serializer(
                instance=two_retina_polygon_annotation_sets.polygonset1
            ).data
            assert response.data == model_serialized

    def test_update_view(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        serializer,
        with_user,
    ):
        model_serialized = serializer(
            instance=two_retina_polygon_annotation_sets.polygonset1
        ).data
        image = ImageFactory()
        model_serialized["image"] = str(image.id)
        model_serialized["singlepolygonannotation_set"] = []
        model_json = json.dumps(model_serialized)

        response = view_test(
            "update",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1,
            rf,
            viewset,
            model_json,
            with_user=with_user,
        )

        if user_type in ("retina_grader", "retina_admin"):
            response.data["image"] = str(response.data["image"])
            response.data["singlepolygonannotation_set"] = []
            assert response.data == model_serialized

    def test_update_view_wrong_user(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        serializer,
        with_user,
    ):
        model_serialized = serializer(
            instance=two_retina_polygon_annotation_sets.polygonset1
        ).data
        image = ImageFactory()
        model_serialized["image"] = str(image.id)
        model_serialized["singlepolygonannotation_set"] = []
        other_user = UserFactory()
        model_serialized["grader"] = other_user.id
        model_json = json.dumps(model_serialized)

        response = view_test(
            "update",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1,
            rf,
            viewset,
            model_json,
            with_user=with_user,
            check_response_status_code=False,
        )
        if user_type == "retina_admin":
            response.data["singlepolygonannotation_set"] = []
            response.data["image"] = str(response.data["image"])
            assert response.data == model_serialized
        elif user_type == "retina_grader":
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert (
                str(response.data["grader"][0])
                == "User is not allowed to create annotation for other grader"
            )
        else:
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_partial_update_view(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        serializer,
        with_user,
    ):
        model_serialized = serializer(
            instance=two_retina_polygon_annotation_sets.polygonset1
        ).data
        image = ImageFactory()
        model_serialized["image"] = str(image.id)
        model_serialized["singlepolygonannotation_set"] = []
        model_json = json.dumps(model_serialized)

        response = view_test(
            "partial_update",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1,
            rf,
            viewset,
            model_json,
            with_user=with_user,
        )

        if user_type in ("retina_grader", "retina_admin"):
            response.data["image"] = str(response.data["image"])
            response.data["singlepolygonannotation_set"] = []
            assert response.data == model_serialized

    def test_destroy_view(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        serializer,
        with_user,
    ):
        view_test(
            "destroy",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1,
            rf,
            viewset,
            with_user=with_user,
        )
        if user_type in ("retina_grader", "retina_admin"):
            assert not PolygonAnnotationSet.objects.filter(
                id=two_retina_polygon_annotation_sets.polygonset1.id
            ).exists()

    def test_destroy_view_wrong_user(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        serializer,
        with_user,
    ):
        response = view_test(
            "destroy",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset2,
            rf,
            viewset,
            with_user=with_user,
            check_response_status_code=False,
        )
        if user_type == "retina_admin":
            assert not PolygonAnnotationSet.objects.filter(
                id=two_retina_polygon_annotation_sets.polygonset2.id
            ).exists()
        elif user_type == "retina_grader":
            assert response.status_code == status.HTTP_404_NOT_FOUND
        else:
            assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_type",
    [
        None,
        "normal_user",
        "retina_grader_non_allowed",
        "retina_grader",
        "retina_admin",
    ],
)
@pytest.mark.parametrize(
    "namespace,basename,viewset,with_user",
    [
        (
            "api",
            "retina-single-polygon-annotation",
            SinglePolygonViewSet,
            False,
        ),
    ],
)
class TestSinglePolygonAnnotationViewSet:
    def test_list_view(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        with_user,
    ):
        response = view_test(
            "list",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader1,
            None,
            rf,
            viewset,
            with_user=with_user,
        )
        if user_type == "retina_grader":
            serialized_data = SinglePolygonAnnotationSerializer(
                two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.all(),
                many=True,
            ).data
            assert len(response.data) == len(serialized_data)
            serialized_data.sort(key=lambda k: k["created"], reverse=True)
            assert response.data == serialized_data
        elif user_type == "retina_admin":
            serialized_data = SinglePolygonAnnotationSerializer(
                two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.all()
                | two_retina_polygon_annotation_sets.polygonset2.singlepolygonannotation_set.all(),
                many=True,
            ).data
            serialized_data.sort(key=lambda k: k["created"], reverse=True)
            assert response.data == serialized_data

    def test_create_view(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        with_user,
    ):
        model_build = SinglePolygonAnnotationFactory.build()
        model_serialized = SinglePolygonAnnotationSerializer(model_build).data
        annotation_set = PolygonAnnotationSetFactory(
            grader=two_retina_polygon_annotation_sets.grader1
        )
        model_serialized["annotation_set"] = str(annotation_set.id)
        model_json = json.dumps(model_serialized)

        response = view_test(
            "create",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader1,
            None,
            rf,
            viewset,
            model_json,
            with_user=with_user,
        )
        if user_type in ("retina_grader", "retina_admin"):
            assert response.data["value"] == model_serialized["value"]

    def test_create_view_wrong_user_id(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        with_user,
    ):
        model_build = SinglePolygonAnnotationFactory.build()
        model_serialized = SinglePolygonAnnotationSerializer(model_build).data
        other_user = UserFactory()
        annotation_set = PolygonAnnotationSetFactory(grader=other_user)
        model_serialized["annotation_set"] = str(annotation_set.id)
        model_json = json.dumps(model_serialized)

        response = view_test(
            "create",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader1,
            None,
            rf,
            viewset,
            model_json,
            with_user=with_user,
            check_response_status_code=False,
        )
        if user_type == "retina_admin":
            assert response.data["value"] == model_serialized["value"]
        elif user_type == "retina_grader":
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert (
                str(response.data["non_field_errors"][0])
                == "User is not allowed to create annotation for other grader"
            )
        else:
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_view(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        with_user,
    ):
        response = view_test(
            "retrieve",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first(),
            rf,
            viewset,
            with_user=with_user,
        )
        if user_type == "retina_grader" or user_type == "retina_admin":
            model_serialized = SinglePolygonAnnotationSerializer(
                two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first()
            ).data
            assert response.data == model_serialized

    def test_update_view(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        with_user,
    ):
        model_serialized = SinglePolygonAnnotationSerializer(
            two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first()
        ).data
        annotation_set = PolygonAnnotationSetFactory(
            grader=two_retina_polygon_annotation_sets.grader1
        )
        model_serialized["annotation_set"] = str(annotation_set.id)
        model_json = json.dumps(model_serialized)

        response = view_test(
            "update",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first(),
            rf,
            viewset,
            model_json,
            with_user=with_user,
        )

        if user_type in ("retina_grader", "retina_admin"):
            response.data["annotation_set"] = str(
                response.data["annotation_set"]
            )
            assert response.data == model_serialized

    def test_update_view_wrong_user_id(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        with_user,
    ):
        model_serialized = SinglePolygonAnnotationSerializer(
            two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first()
        ).data
        annotation_set = PolygonAnnotationSetFactory()
        model_serialized["annotation_set"] = str(annotation_set.id)
        model_json = json.dumps(model_serialized)

        response = view_test(
            "update",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first(),
            rf,
            viewset,
            model_json,
            with_user=with_user,
            check_response_status_code=False,
        )
        if user_type == "retina_admin":
            model_serialized["id"] = response.data["id"]
            response.data["annotation_set"] = str(
                response.data["annotation_set"]
            )
            assert response.data == model_serialized
        elif user_type == "retina_grader":
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert (
                str(response.data["non_field_errors"][0])
                == "User is not allowed to create annotation for other grader"
            )
        else:
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_partial_update_view(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        with_user,
    ):
        model_serialized = SinglePolygonAnnotationSerializer(
            two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first()
        ).data
        annotation_set = SinglePolygonAnnotationFactory()
        model_serialized["value"] = annotation_set.value
        partial_model = copy.deepcopy(model_serialized)
        del partial_model["annotation_set"]
        del partial_model["id"]
        model_json = json.dumps(partial_model)

        response = view_test(
            "partial_update",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first(),
            rf,
            viewset,
            model_json,
            with_user=with_user,
        )

        if user_type in ("retina_grader", "retina_admin"):
            assert response.data == model_serialized

    def test_destroy_view(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        with_user,
    ):
        view_test(
            "destroy",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first(),
            rf,
            viewset,
            with_user=with_user,
        )
        if user_type in ("retina_grader", "retina_admin"):
            assert not PolygonAnnotationSet.objects.filter(
                id=two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first().id
            ).exists()

    def test_destroy_view_wrong_user(
        self,
        two_retina_polygon_annotation_sets,
        rf,
        user_type,
        namespace,
        basename,
        viewset,
        with_user,
    ):
        response = view_test(
            "destroy",
            user_type,
            namespace,
            basename,
            two_retina_polygon_annotation_sets.grader2,
            two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first(),
            rf,
            viewset,
            with_user=with_user,
            check_response_status_code=False,
        )
        if user_type == "retina_admin":
            assert not PolygonAnnotationSet.objects.filter(
                id=two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first().id
            ).exists()
        elif user_type == "retina_grader":
            assert response.status_code == status.HTTP_404_NOT_FOUND
        else:
            assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_type",
    [
        None,
        "normal_user",
        "retina_grader_non_allowed",
        "retina_grader",
        "retina_admin",
    ],
)
@pytest.mark.parametrize(
    "viewset,factory,serializer,basename,with_user",
    (
        (
            QualityAnnotationViewSet,
            ImageQualityAnnotationFactory,
            ImageQualityAnnotationSerializer,
            "retina-quality-annotation",
            False,
        ),
        (
            PathologyAnnotationViewSet,
            ImagePathologyAnnotationFactory,
            ImagePathologyAnnotationSerializer,
            "retina-pathology-annotation",
            False,
        ),
        (
            RetinaPathologyAnnotationViewSet,
            RetinaImagePathologyAnnotationFactory,
            RetinaImagePathologyAnnotationSerializer,
            "retina-retina-pathology-annotation",
            False,
        ),
        (
            OctRetinaPathologyAnnotationViewSet,
            OctRetinaImagePathologyAnnotationFactory,
            OctRetinaImagePathologyAnnotationSerializer,
            "oct-retina-retina-pathology-annotation",
            False,
        ),
        (
            TextAnnotationViewSet,
            ImageTextAnnotationFactory,
            ImageTextAnnotationSerializer,
            "retina-text-annotation",
            False,
        ),
        (
            PolygonAnnotationSetViewSet,
            PolygonAnnotationSetFactory,
            NestedPolygonAnnotationSetSerializer,
            "retina-polygon-annotation-set",
            False,
        ),
        (
            BooleanClassificationAnnotationViewSet,
            BooleanClassificationAnnotationFactory,
            BooleanClassificationAnnotationSerializer,
            "retina-boolean-classification-annotation",
            False,
        ),
        (
            ETDRSGridAnnotationViewSet,
            ETDRSGridAnnotationFactory,
            ETDRSGridAnnotationSerializer,
            "retina-etdrs-grid-annotation",
            False,
        ),
    ),
)
class TestAnnotationViewSets:
    namespace = "retina:api"

    @staticmethod
    def create_models(factory):
        graders = [UserFactory(), UserFactory(), UserFactory()]
        add_to_graders_group(graders)
        model = factory(grader=graders[0])
        models = [
            model,
            factory(grader=graders[0]),
            factory(grader=graders[1]),
            factory(grader=graders[2]),
        ]

        return models

    def test_list_view(
        self, rf, user_type, viewset, factory, serializer, basename, with_user
    ):
        models = self.create_models(factory)
        response = view_test(
            "list",
            user_type,
            self.namespace if basename is None else "api",
            basename
            if basename is not None
            else factory._meta.model._meta.model_name,
            models[0].grader,
            None,
            rf,
            viewset,
            with_user=with_user,
        )
        if user_type == "retina_grader":
            serialized_data = serializer(models[0:2], many=True).data
            assert len(response.data) == len(serialized_data)
            serialized_data.sort(key=lambda k: k["created"], reverse=True)
            assert response.data == serialized_data
        elif user_type == "retina_admin":
            serialized_data = serializer(models, many=True).data
            serialized_data.sort(key=lambda k: k["created"], reverse=True)
            assert len(response.data) == len(serialized_data)
            assert response.data == serialized_data

    def test_create_view(
        self, rf, user_type, viewset, factory, serializer, basename, with_user
    ):
        models = self.create_models(factory)
        build_kwargs = {"grader": models[0].grader}
        build_kwargs.update({"image": models[0].image})
        model_build = factory.build(**build_kwargs)
        model_serialized = serializer(model_build).data
        model_serialized["grader"] = models[0].grader.id
        model_serialized["image"] = str(model_serialized["image"])
        model_json = json.dumps(model_serialized)

        response = view_test(
            "create",
            user_type,
            self.namespace if basename is None else "api",
            basename
            if basename is not None
            else factory._meta.model._meta.model_name,
            models[0].grader,
            None,
            rf,
            viewset,
            model_json,
            with_user=with_user,
        )
        if user_type in ("retina_grader", "retina_admin"):
            model_serialized["id"] = response.data["id"]
            response.data["image"] = str(response.data["image"])
            assert response.data == model_serialized

    def test_create_view_wrong_user_id(
        self, rf, user_type, viewset, factory, serializer, basename, with_user
    ):
        models = self.create_models(factory)
        build_kwargs = {"grader": models[0].grader}
        build_kwargs.update({"image": ImageFactory()})
        model_build = factory.build(**build_kwargs)
        model_serialized = serializer(model_build).data
        model_serialized["grader"] = models[2].grader.id
        model_serialized["image"] = str(model_serialized["image"])
        model_json = json.dumps(model_serialized)

        response = view_test(
            "create",
            user_type,
            self.namespace if basename is None else "api",
            basename
            if basename is not None
            else factory._meta.model._meta.model_name,
            models[0].grader,
            None,
            rf,
            viewset,
            model_json,
            with_user=with_user,
            check_response_status_code=False,
        )
        if user_type == "retina_admin":
            model_serialized["id"] = response.data["id"]
            response.data["image"] = str(response.data["image"])
            assert response.data == model_serialized
        elif user_type == "retina_grader":
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert (
                str(response.data["grader"][0])
                == "User is not allowed to create annotation for other grader"
            )
        else:
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_view(
        self, rf, user_type, viewset, factory, serializer, basename, with_user
    ):
        models = self.create_models(factory)
        response = view_test(
            "retrieve",
            user_type,
            self.namespace if basename is None else "api",
            basename
            if basename is not None
            else factory._meta.model._meta.model_name,
            models[0].grader,
            models[0],
            rf,
            viewset,
            with_user=with_user,
        )
        if user_type == "retina_grader" or user_type == "retina_admin":
            model_serialized = serializer(models[0]).data
            assert response.data == model_serialized

    def test_update_view(
        self, rf, user_type, viewset, factory, serializer, basename, with_user
    ):
        models = self.create_models(factory)
        model_serialized = serializer(models[1]).data
        models[1].delete()
        model_serialized["image"] = str(model_serialized["image"])
        model_serialized["id"] = str(models[0].id)
        model_json = json.dumps(model_serialized)

        response = view_test(
            "update",
            user_type,
            self.namespace if basename is None else "api",
            basename
            if basename is not None
            else factory._meta.model._meta.model_name,
            models[0].grader,
            models[0],
            rf,
            viewset,
            model_json,
            with_user=with_user,
        )

        if user_type in ("retina_grader", "retina_admin"):
            response.data["image"] = str(response.data["image"])
            assert response.data == model_serialized

    def test_update_view_wrong_user_id(
        self, rf, user_type, viewset, factory, serializer, basename, with_user
    ):
        other_user = UserFactory()
        models = self.create_models(factory)
        model_serialized = serializer(models[0]).data
        model_serialized["image"] = str(model_serialized["image"])
        model_serialized["grader"] = other_user.id
        model_json = json.dumps(model_serialized)

        response = view_test(
            "update",
            user_type,
            self.namespace if basename is None else "api",
            basename
            if basename is not None
            else factory._meta.model._meta.model_name,
            models[0].grader,
            models[0],
            rf,
            viewset,
            model_json,
            with_user=with_user,
            check_response_status_code=False,
        )
        if user_type == "retina_admin":
            model_serialized["id"] = response.data["id"]
            response.data["image"] = str(response.data["image"])
            assert response.data == model_serialized
        elif user_type == "retina_grader":
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert (
                str(response.data["grader"][0])
                == "User is not allowed to create annotation for other grader"
            )
        else:
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_partial_update_view(
        self, rf, user_type, viewset, factory, serializer, basename, with_user
    ):
        models = self.create_models(factory)
        model_serialized = serializer(models[0]).data
        partial_model = copy.deepcopy(model_serialized)
        del partial_model["image"]
        del partial_model["id"]
        del partial_model["grader"]
        model_json = json.dumps(partial_model)

        response = view_test(
            "partial_update",
            user_type,
            self.namespace if basename is None else "api",
            basename
            if basename is not None
            else factory._meta.model._meta.model_name,
            models[0].grader,
            models[0],
            rf,
            viewset,
            model_json,
            with_user=with_user,
        )

        if user_type in ("retina_grader", "retina_admin"):
            assert response.data == model_serialized

    def test_destroy_view(
        self, rf, user_type, viewset, factory, serializer, basename, with_user
    ):
        models = self.create_models(factory)
        view_test(
            "destroy",
            user_type,
            self.namespace if basename is None else "api",
            basename
            if basename is not None
            else factory._meta.model._meta.model_name,
            models[0].grader,
            models[0],
            rf,
            viewset,
            with_user=with_user,
        )
        if user_type in ("retina_grader", "retina_admin"):
            assert not factory._meta.model.objects.filter(
                id=models[0].id
            ).exists()

    def test_destroy_view_wrong_user(
        self, rf, user_type, viewset, factory, serializer, basename, with_user
    ):
        models = self.create_models(factory)
        response = view_test(
            "destroy",
            user_type,
            self.namespace if basename is None else "api",
            basename
            if basename is not None
            else factory._meta.model._meta.model_name,
            models[2].grader,
            models[0],
            rf,
            viewset,
            with_user=with_user,
            check_response_status_code=False,
        )
        if user_type == "retina_admin":
            assert not factory._meta.model.objects.filter(
                id=models[0].id
            ).exists()
        elif user_type == "retina_grader":
            assert response.status_code == status.HTTP_404_NOT_FOUND
        else:
            assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_type", [None, "normal_user", "retina_grader", "retina_admin"]
)
@pytest.mark.parametrize(
    "viewset,factory,serializer,basename,",
    (
        (
            LandmarkAnnotationSetViewSet,
            LandmarkAnnotationSetFactory,
            LandmarkAnnotationSetSerializer,
            "retina-landmark-annotation",
        ),
    ),
)
class TestLandmarkAnnotationSetViewSet:
    namespace = "api"

    @staticmethod
    def create_models(factory):
        graders = [UserFactory(), UserFactory(), UserFactory()]
        add_to_graders_group(graders)
        model = factory(grader=graders[0])
        models = [
            model,
            factory(grader=graders[0]),
            factory(grader=graders[1]),
            factory(grader=graders[2]),
        ]

        return models

    def test_list_view(
        self, rf, user_type, viewset, factory, serializer, basename
    ):
        models = self.create_models(factory)
        response = view_test(
            "list",
            user_type,
            self.namespace,
            basename,
            models[0].grader,
            None,
            rf,
            viewset,
            with_user=False,
        )
        if user_type == "retina_grader":
            serialized_data = serializer(models[0:2], many=True).data
            assert len(response.data) == len(serialized_data)
            serialized_data.sort(key=lambda k: k["created"], reverse=True)
            assert response.data == serialized_data
        elif user_type == "retina_admin":
            serialized_data = serializer(models, many=True).data
            serialized_data.sort(key=lambda k: k["created"], reverse=True)
            assert len(response.data) == len(serialized_data)
            assert response.data == serialized_data

    def test_create_view(
        self, rf, user_type, viewset, factory, serializer, basename
    ):
        models = self.create_models(factory)
        build_kwargs = {"grader": models[0].grader}
        model_build = factory.build(**build_kwargs)
        model_serialized = serializer(model_build).data
        model_serialized["grader"] = models[0].grader.id
        model_json = json.dumps(model_serialized)

        response = view_test(
            "create",
            user_type,
            self.namespace,
            basename,
            models[0].grader,
            None,
            rf,
            viewset,
            model_json,
            with_user=False,
        )
        if user_type in ("retina_grader", "retina_admin"):
            model_serialized["id"] = response.data["id"]
            assert response.data == model_serialized

    def test_create_view_wrong_user_id(
        self, rf, user_type, viewset, factory, serializer, basename
    ):
        models = self.create_models(factory)
        build_kwargs = {"grader": models[0].grader}
        model_build = factory.build(**build_kwargs)
        model_serialized = serializer(model_build).data
        model_serialized["grader"] = models[2].grader.id
        model_json = json.dumps(model_serialized)

        response = view_test(
            "create",
            user_type,
            self.namespace,
            basename,
            models[0].grader,
            None,
            rf,
            viewset,
            model_json,
            check_response_status_code=False,
            with_user=False,
        )
        if user_type == "retina_admin":
            model_serialized["id"] = response.data["id"]
            assert response.data == model_serialized
        elif user_type == "retina_grader":
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert (
                str(response.data["grader"][0])
                == "User is not allowed to create annotation for other grader"
            )
        else:
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_view_no_user_id(
        self, rf, user_type, viewset, factory, serializer, basename
    ):
        models = self.create_models(factory)
        build_kwargs = {"grader": models[0].grader}
        model_build = factory.build(**build_kwargs)
        model_serialized = serializer(model_build).data
        model_serialized_no_grader = model_serialized.copy()
        del model_serialized_no_grader["grader"]
        model_json = json.dumps(model_serialized_no_grader)

        response = view_test(
            "create",
            user_type,
            self.namespace,
            basename,
            models[0].grader,
            None,
            rf,
            viewset,
            model_json,
            check_response_status_code=False,
            with_user=False,
        )
        if user_type in ("retina_admin", "retina_grader"):
            model_serialized["id"] = response.data["id"]
            if user_type == "retina_admin":
                model_serialized["grader"] = response.data["grader"]
            assert response.data == model_serialized
        else:
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_view(
        self, rf, user_type, viewset, factory, serializer, basename
    ):
        models = self.create_models(factory)
        response = view_test(
            "retrieve",
            user_type,
            self.namespace,
            basename,
            models[0].grader,
            models[0],
            rf,
            viewset,
            with_user=False,
        )
        if user_type == "retina_grader" or user_type == "retina_admin":
            model_serialized = serializer(models[0]).data
            assert response.data == model_serialized

    def test_update_view(
        self, rf, user_type, viewset, factory, serializer, basename
    ):
        models = self.create_models(factory)
        model_serialized = serializer(models[1]).data
        models[1].delete()
        model_serialized["id"] = str(models[0].id)
        model_json = json.dumps(model_serialized)

        response = view_test(
            "update",
            user_type,
            self.namespace,
            basename,
            models[0].grader,
            models[0],
            rf,
            viewset,
            model_json,
            with_user=False,
        )

        if user_type in ("retina_grader", "retina_admin"):
            assert response.data != model_serialized

    def test_update_view_wrong_user_id(
        self, rf, user_type, viewset, factory, serializer, basename
    ):
        other_user = UserFactory()
        models = self.create_models(factory)
        model_serialized = serializer(models[0]).data
        model_serialized["grader"] = other_user.id
        model_json = json.dumps(model_serialized)

        response = view_test(
            "update",
            user_type,
            self.namespace,
            basename,
            models[0].grader,
            models[0],
            rf,
            viewset,
            model_json,
            check_response_status_code=False,
            with_user=False,
        )
        if user_type == "retina_admin":
            model_serialized["id"] = response.data["id"]
            assert response.data != model_serialized
        elif user_type == "retina_grader":
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert (
                str(response.data["grader"][0])
                == "User is not allowed to create annotation for other grader"
            )
        else:
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_partial_update_view(
        self, rf, user_type, viewset, factory, serializer, basename
    ):
        models = self.create_models(factory)
        model_serialized = serializer(models[0]).data
        partial_model = copy.deepcopy(model_serialized)
        del partial_model["id"]
        del partial_model["grader"]
        model_json = json.dumps(partial_model)

        response = view_test(
            "partial_update",
            user_type,
            self.namespace,
            basename,
            models[0].grader,
            models[0],
            rf,
            viewset,
            model_json,
            with_user=False,
        )

        if user_type in ("retina_grader", "retina_admin"):
            assert response.data == model_serialized

    def test_destroy_view(
        self, rf, user_type, viewset, factory, serializer, basename
    ):
        models = self.create_models(factory)
        view_test(
            "destroy",
            user_type,
            self.namespace,
            basename,
            models[0].grader,
            models[0],
            rf,
            viewset,
            with_user=False,
        )
        if user_type in ("retina_grader", "retina_admin"):
            assert not factory._meta.model.objects.filter(
                id=models[0].id
            ).exists()

    def test_destroy_view_wrong_user(
        self, rf, user_type, viewset, factory, serializer, basename
    ):
        models = self.create_models(factory)
        response = view_test(
            "destroy",
            user_type,
            self.namespace,
            basename,
            models[2].grader,
            models[0],
            rf,
            viewset,
            check_response_status_code=False,
            with_user=False,
        )
        if user_type == "retina_admin":
            assert not factory._meta.model.objects.filter(
                id=models[0].id
            ).exists()
        elif user_type == "retina_grader":
            assert response.status_code == status.HTTP_404_NOT_FOUND
        else:
            assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_type", [None, "normal_user", "retina_grader", "retina_admin"]
)
class TestLandmarkAnnotationSetViewSetForImage:
    @staticmethod
    def perform_request(rf, user_type, querystring, data=None):
        kwargs = {}
        if data is not None:
            kwargs.update({"grader": data.grader1})

        user = get_user_from_user_type(user_type, **kwargs)

        url = reverse("api:retina-landmark-annotation-list") + querystring

        request = rf.get(url)

        force_authenticate(request, user=user)
        view = LandmarkAnnotationSetViewSet.as_view(actions={"get": "list"})
        return view(request)

    def test_no_query_params(self, rf, user_type):
        response = self.perform_request(rf, user_type, "")

        if user_type in (None, "normal_user"):
            assert response.status_code == status.HTTP_403_FORBIDDEN
        else:
            assert response.status_code == status.HTTP_200_OK

    def test_invalid_image_uuid(self, rf, user_type):
        response = self.perform_request(
            rf, user_type, "?image_id=invalid_uuid"
        )

        if user_type in (None, "normal_user"):
            assert response.status_code == status.HTTP_403_FORBIDDEN
        else:
            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_non_existant_image(self, rf, user_type):
        img = ImageFactory()
        pk = img.pk
        img.delete()
        response = self.perform_request(rf, user_type, f"?image_id={pk}")

        if user_type in (None, "normal_user"):
            assert response.status_code == status.HTTP_403_FORBIDDEN
        else:
            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_non_annotation_image(self, rf, user_type):
        img = ImageFactory()
        response = self.perform_request(rf, user_type, f"?image_id={img.pk}")

        if user_type in (None, "normal_user"):
            assert response.status_code == status.HTTP_403_FORBIDDEN
        else:
            assert response.status_code == status.HTTP_200_OK
            assert len(response.data) == 0

    def test_annotation_image(
        self, rf, user_type, multiple_landmark_retina_annotation_sets
    ):
        img = multiple_landmark_retina_annotation_sets.landmarkset1images[0]
        response = self.perform_request(
            rf,
            user_type,
            f"?image_id={img.pk}",
            data=multiple_landmark_retina_annotation_sets,
        )

        if user_type == "retina_grader":
            assert response.status_code == status.HTTP_200_OK
            assert len(response.data) == 2
            serialized_data = LandmarkAnnotationSetSerializer(
                [
                    multiple_landmark_retina_annotation_sets.landmarkset1,
                    multiple_landmark_retina_annotation_sets.landmarkset3,
                ],
                many=True,
            ).data
            serialized_data.sort(key=lambda k: k["created"], reverse=True)
            assert response.data == serialized_data
        elif user_type == "retina_admin":
            assert response.status_code == status.HTTP_200_OK
            assert len(response.data) == 3
            serialized_data = LandmarkAnnotationSetSerializer(
                [
                    multiple_landmark_retina_annotation_sets.landmarkset1,
                    multiple_landmark_retina_annotation_sets.landmarkset3,
                    multiple_landmark_retina_annotation_sets.landmarkset4,
                ],
                many=True,
            ).data
            serialized_data.sort(key=lambda k: k["created"], reverse=True)
        else:
            assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.parametrize(
    "user_type", [None, "normal_user", "retina_grader", "retina_admin"]
)
class TestImageLevelAnnotationsForImageViewSet:
    @staticmethod
    def perform_request(rf, user_type, image_id=None, grader=None):
        kwargs = {"pk": image_id}
        user = get_user_from_user_type(user_type, grader=grader)

        url = reverse(
            "api:retina-image-level-annotation-for-image-detail", kwargs=kwargs
        )

        request = rf.get(url)

        force_authenticate(request, user=user)
        view = ImageLevelAnnotationsForImageViewSet.as_view(
            actions={"get": "retrieve"}
        )
        return view(request, **kwargs)

    def test_no_image_id(self, rf, user_type):
        response = self.perform_request(rf, user_type)

        if user_type in (None, "normal_user"):
            assert response.status_code == status.HTTP_403_FORBIDDEN
        else:
            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_non_existant_image(self, rf, user_type):
        img = ImageFactory()
        pk = img.pk
        img.delete()
        response = self.perform_request(rf, user_type, image_id=pk)

        if user_type in (None, "normal_user"):
            assert response.status_code == status.HTTP_403_FORBIDDEN
        else:
            assert response.status_code == status.HTTP_200_OK
            assert response.data == {
                "quality": None,
                "pathology": None,
                "retina_pathology": None,
                "oct_retina_pathology": None,
                "text": None,
            }

    def test_non_annotation_image(self, rf, user_type):
        img = ImageFactory()
        response = self.perform_request(rf, user_type, image_id=img.pk)

        if user_type in (None, "normal_user"):
            assert response.status_code == status.HTTP_403_FORBIDDEN
        else:
            assert response.status_code == status.HTTP_200_OK
            assert response.data == {
                "quality": None,
                "pathology": None,
                "retina_pathology": None,
                "oct_retina_pathology": None,
                "text": None,
            }

    def test_annotation_image_wrong_user(
        self, rf, user_type, image_with_image_level_annotations
    ):
        image, grader, annotations = image_with_image_level_annotations
        response = self.perform_request(rf, user_type, image_id=image.pk)
        if user_type in (None, "normal_user"):
            assert response.status_code == status.HTTP_403_FORBIDDEN
        else:
            assert response.status_code == status.HTTP_200_OK
            assert response.data == {
                "quality": None,
                "pathology": None,
                "retina_pathology": None,
                "oct_retina_pathology": None,
                "text": None,
            }

    def test_annotation_image_correct_user(
        self, rf, user_type, image_with_image_level_annotations
    ):
        image, grader, annotations = image_with_image_level_annotations
        response = self.perform_request(
            rf, user_type, image_id=image.pk, grader=grader
        )

        if user_type == "retina_admin":
            assert response.status_code == status.HTTP_200_OK
            assert response.data == {
                "quality": None,
                "pathology": None,
                "retina_pathology": None,
                "oct_retina_pathology": None,
                "text": None,
            }
        elif user_type == "retina_grader":
            assert response.status_code == status.HTTP_200_OK
            assert response.data == {
                "quality": str(annotations["quality"].id),
                "pathology": str(annotations["pathology"].id),
                "retina_pathology": str(annotations["retina_pathology"].id),
                "oct_retina_pathology": str(
                    annotations["oct_retina_pathology"].id
                ),
                "text": str(annotations["text"].id),
            }
        else:
            assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestPolygonAnnotationSetViewSetWithImageFilter:
    @staticmethod
    def perform_request(rf, image_id, user):
        url = f"{reverse('api:retina-polygon-annotation-set-list')}?image={image_id}"
        request = rf.get(url)
        force_authenticate(request, user=user)
        view = PolygonAnnotationSetViewSet.as_view(actions={"get": "list"})
        return view(request)

    def test_filter_nonexistant_image(
        self, rf, two_retina_polygon_annotation_sets
    ):
        grader = two_retina_polygon_annotation_sets.grader1
        response = self.perform_request(
            rf, "00000000-0000-0000-0000-000000000000", grader
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_filter_all(self, rf, two_retina_polygon_annotation_sets):
        image = two_retina_polygon_annotation_sets.polygonset1.image
        grader = two_retina_polygon_annotation_sets.grader1
        response = self.perform_request(rf, image.id, grader)
        assert response.status_code == status.HTTP_200_OK
        serialized_data = NestedPolygonAnnotationSetSerializer(
            two_retina_polygon_annotation_sets.polygonset1
        ).data
        assert response.data == [serialized_data]

    def test_filter_other(self, rf, two_retina_polygon_annotation_sets):
        grader = two_retina_polygon_annotation_sets.grader1
        polygonset3 = PolygonAnnotationSetFactory(grader=grader)
        response = self.perform_request(rf, polygonset3.image.id, grader)
        assert response.status_code == status.HTTP_200_OK
        serialized_data = NestedPolygonAnnotationSetSerializer(
            polygonset3
        ).data
        assert response.data == [serialized_data]


@pytest.mark.django_db
class TestRetinaImageViewSetNumQueries:
    @staticmethod
    def perform_request(rf, user):
        url = reverse("api:retina-images-list")
        request = rf.get(url)
        force_authenticate(request, user=user)
        view = RetinaImageViewSet.as_view(actions={"get": "list"})
        return view(request)

    def test_no_landmarks(self, rf, django_assert_max_num_queries):
        u = UserFactory()
        i = ImageFactory()
        assign_perm("view_image", u, i)
        with django_assert_max_num_queries(6):
            response = self.perform_request(rf, u)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert len(response.data["results"][0]["landmark_annotations"]) == 0

    def test_one_landmark(self, rf, django_assert_max_num_queries):
        u = UserFactory()
        i1 = ImageFactory()
        i2 = ImageFactory()
        assign_perm("view_image", u, i1)
        assign_perm("view_image", u, i2)
        las = LandmarkAnnotationSetFactory(grader=u)
        SingleLandmarkAnnotationFactory(annotation_set=las, image=i1)
        SingleLandmarkAnnotationFactory(annotation_set=las, image=i2)
        with django_assert_max_num_queries(9):
            response = self.perform_request(rf, u)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2
        assert len(response.data["results"][0]["landmark_annotations"]) == 1
        assert len(response.data["results"][1]["landmark_annotations"]) == 1

    def test_multiple_landmarks(self, rf, django_assert_max_num_queries):
        u = UserFactory()
        for _ in range(4):
            img = ImageFactory()
            assign_perm("view_image", u, img)
            las = LandmarkAnnotationSetFactory(grader=u)
            SingleLandmarkAnnotationFactory(annotation_set=las, image=img)
            SingleLandmarkAnnotationFactory(annotation_set=las)
        with django_assert_max_num_queries(9):
            response = self.perform_request(rf, u)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 4

    def test_multiple_landmarks_24(self, rf, django_assert_max_num_queries):
        u = UserFactory()
        for _ in range(24):
            img = ImageFactory()
            assign_perm("view_image", u, img)
            las = LandmarkAnnotationSetFactory(grader=u)
            SingleLandmarkAnnotationFactory(annotation_set=las, image=img)
            SingleLandmarkAnnotationFactory(annotation_set=las)
        with django_assert_max_num_queries(9):
            response = self.perform_request(rf, u)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 24
