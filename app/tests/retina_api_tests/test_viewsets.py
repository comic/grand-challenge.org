import copy
import json

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from grandchallenge.annotations.models import (
    ETDRSGridAnnotation,
    PolygonAnnotationSet,
)
from grandchallenge.annotations.serializers import (
    ETDRSGridAnnotationSerializer,
    ImagePathologyAnnotationSerializer,
    ImageQualityAnnotationSerializer,
    ImageTextAnnotationSerializer,
    LandmarkAnnotationSetSerializer,
    PolygonAnnotationSetSerializer,
    RetinaImagePathologyAnnotationSerializer,
    SinglePolygonAnnotationSerializer,
)
from grandchallenge.core.serializers import UserSerializer
from grandchallenge.registrations.serializers import (
    OctObsRegistrationSerializer,
)
from grandchallenge.retina_api.views import (
    ETDRSGridAnnotationViewSet,
    GradersWithPolygonAnnotationsListView,
    ImagePathologyAnnotationViewSet,
    ImageQualityAnnotationViewSet,
    ImageTextAnnotationViewSet,
    LandmarkAnnotationSetForImageList,
    LandmarkAnnotationSetViewSet,
    OctObsRegistrationRetrieve,
    PolygonAnnotationSetViewSet,
    PolygonListView,
    RetinaImagePathologyAnnotationViewSet,
    SinglePolygonViewSet,
)
from grandchallenge.subdomains.utils import reverse
from tests.annotations_tests.factories import (
    ETDRSGridAnnotationFactory,
    ImagePathologyAnnotationFactory,
    ImageQualityAnnotationFactory,
    ImageTextAnnotationFactory,
    LandmarkAnnotationSetFactory,
    PolygonAnnotationSetFactory,
    RetinaImagePathologyAnnotationFactory,
    SinglePolygonAnnotationFactory,
)
from tests.cases_tests.factories import ImageFactory
from tests.conftest import (
    add_to_graders_group,
    generate_annotation_set,
    generate_multiple_landmark_annotation_sets,
    generate_two_polygon_annotation_sets,
)
from tests.factories import UserFactory
from tests.registrations_tests.factories import OctObsRegistrationFactory
from tests.viewset_helpers import get_user_from_user_type, view_test


class TestPolygonAPIListView(TestCase):
    def setUp(self):
        self.annotation_set = generate_annotation_set(retina_grader=True)
        self.kwargs = {
            "user_id": self.annotation_set.grader.id,
            "image_id": self.annotation_set.polygon.image.id,
        }
        self.url = reverse(
            "retina:api:polygon-annotation-list-view", kwargs=self.kwargs
        )
        self.view = PolygonListView.as_view()
        self.rf = APIRequestFactory()
        self.request = self.rf.get(self.url)
        self.serialized_data = PolygonAnnotationSetSerializer(
            instance=self.annotation_set.polygon
        )

    def test_polygon_list_api_view_non_authenticated(self):
        response = self.view(self.request, **self.kwargs)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_polygon_list_api_view_non_retina_user(self):
        self.annotation_set.grader.groups.clear()
        force_authenticate(self.request, user=self.annotation_set.grader)
        response = self.view(self.request, **self.kwargs)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_polygon_list_api_view_owner_authenticated(self):
        force_authenticate(self.request, user=self.annotation_set.grader)
        response = self.view(self.request, **self.kwargs)

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0] == self.serialized_data.data

    def test_polygon_list_api_view_admin_authenticated(self):
        retina_admin = UserFactory()
        retina_admin.groups.add(
            Group.objects.get(name=settings.RETINA_ADMINS_GROUP_NAME)
        )
        force_authenticate(self.request, user=retina_admin)
        response = self.view(self.request, **self.kwargs)

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0] == self.serialized_data.data


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
class TestPolygonAnnotationSetViewSet:
    namespace = "retina:api"
    basename = "polygonannotationset"

    def test_list_view(
        self, two_retina_polygon_annotation_sets, rf, user_type
    ):
        response = view_test(
            "list",
            user_type,
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1,
            rf,
            PolygonAnnotationSetViewSet,
        )
        if user_type == "retina_grader":
            serialized_data = PolygonAnnotationSetSerializer(
                two_retina_polygon_annotation_sets.polygonset1
            ).data
            assert response.data == [serialized_data]
        if user_type == "retina_admin":
            serialized_data = PolygonAnnotationSetSerializer(
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
        self, two_retina_polygon_annotation_sets, rf, user_type
    ):
        model_build = PolygonAnnotationSetFactory.build()
        model_serialized = PolygonAnnotationSetSerializer(model_build).data
        image = ImageFactory()
        model_serialized["image"] = str(image.id)
        model_serialized[
            "grader"
        ] = two_retina_polygon_annotation_sets.grader1.id
        model_json = json.dumps(model_serialized)

        response = view_test(
            "create",
            user_type,
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1,
            rf,
            PolygonAnnotationSetViewSet,
            model_json,
        )
        if user_type in ("retina_grader", "retina_admin"):
            model_serialized["id"] = response.data["id"]
            response.data["image"] = str(response.data["image"])
            assert response.data == model_serialized

    def test_create_view_wrong_user_id(
        self, two_retina_polygon_annotation_sets, rf, user_type
    ):
        model_build = PolygonAnnotationSetFactory.build()
        model_serialized = PolygonAnnotationSetSerializer(model_build).data
        image = ImageFactory()
        model_serialized["image"] = str(image.id)
        other_user = UserFactory()
        model_serialized["grader"] = other_user.id
        model_json = json.dumps(model_serialized)

        response = view_test(
            "create",
            user_type,
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1,
            rf,
            PolygonAnnotationSetViewSet,
            model_json,
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
        self, two_retina_polygon_annotation_sets, rf, user_type
    ):
        response = view_test(
            "retrieve",
            user_type,
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1,
            rf,
            PolygonAnnotationSetViewSet,
        )
        if user_type == "retina_grader" or user_type == "retina_admin":
            model_serialized = PolygonAnnotationSetSerializer(
                instance=two_retina_polygon_annotation_sets.polygonset1
            ).data
            assert response.data == model_serialized

    def test_update_view(
        self, two_retina_polygon_annotation_sets, rf, user_type
    ):
        model_serialized = PolygonAnnotationSetSerializer(
            instance=two_retina_polygon_annotation_sets.polygonset1
        ).data
        image = ImageFactory()
        model_serialized["image"] = str(image.id)
        model_serialized["singlepolygonannotation_set"] = []
        model_json = json.dumps(model_serialized)

        response = view_test(
            "update",
            user_type,
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1,
            rf,
            PolygonAnnotationSetViewSet,
            model_json,
        )

        if user_type in ("retina_grader", "retina_admin"):
            response.data["image"] = str(response.data["image"])
            response.data["singlepolygonannotation_set"] = []
            assert response.data == model_serialized

    def test_update_view_wrong_user(
        self, two_retina_polygon_annotation_sets, rf, user_type
    ):
        model_serialized = PolygonAnnotationSetSerializer(
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
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1,
            rf,
            PolygonAnnotationSetViewSet,
            model_json,
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
        self, two_retina_polygon_annotation_sets, rf, user_type
    ):
        model_serialized = PolygonAnnotationSetSerializer(
            instance=two_retina_polygon_annotation_sets.polygonset1
        ).data
        image = ImageFactory()
        model_serialized["image"] = str(image.id)
        model_serialized["singlepolygonannotation_set"] = []
        model_json = json.dumps(model_serialized)

        response = view_test(
            "partial_update",
            user_type,
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1,
            rf,
            PolygonAnnotationSetViewSet,
            model_json,
        )

        if user_type in ("retina_grader", "retina_admin"):
            response.data["image"] = str(response.data["image"])
            response.data["singlepolygonannotation_set"] = []
            assert response.data == model_serialized

    def test_destroy_view(
        self, two_retina_polygon_annotation_sets, rf, user_type
    ):
        view_test(
            "destroy",
            user_type,
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1,
            rf,
            PolygonAnnotationSetViewSet,
        )
        if user_type in ("retina_grader", "retina_admin"):
            assert not PolygonAnnotationSet.objects.filter(
                id=two_retina_polygon_annotation_sets.polygonset1.id
            ).exists()

    def test_destroy_view_wrong_user(
        self, two_retina_polygon_annotation_sets, rf, user_type
    ):
        response = view_test(
            "destroy",
            user_type,
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset2,
            rf,
            PolygonAnnotationSetViewSet,
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
class TestSinglePolygonAnnotationViewSet:
    namespace = "retina:api"
    basename = "singlepolygonannotation"

    def test_list_view(
        self, two_retina_polygon_annotation_sets, rf, user_type
    ):
        response = view_test(
            "list",
            user_type,
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader1,
            None,
            rf,
            SinglePolygonViewSet,
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
        self, two_retina_polygon_annotation_sets, rf, user_type
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
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader1,
            None,
            rf,
            SinglePolygonViewSet,
            model_json,
        )
        if user_type in ("retina_grader", "retina_admin"):
            assert response.data["value"] == model_serialized["value"]

    def test_create_view_wrong_user_id(
        self, two_retina_polygon_annotation_sets, rf, user_type
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
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader1,
            None,
            rf,
            SinglePolygonViewSet,
            model_json,
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
        self, two_retina_polygon_annotation_sets, rf, user_type
    ):
        response = view_test(
            "retrieve",
            user_type,
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first(),
            rf,
            SinglePolygonViewSet,
        )
        if user_type == "retina_grader" or user_type == "retina_admin":
            model_serialized = SinglePolygonAnnotationSerializer(
                two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first()
            ).data
            assert response.data == model_serialized

    def test_update_view(
        self, two_retina_polygon_annotation_sets, rf, user_type
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
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first(),
            rf,
            SinglePolygonViewSet,
            model_json,
        )

        if user_type in ("retina_grader", "retina_admin"):
            response.data["annotation_set"] = str(
                response.data["annotation_set"]
            )
            assert response.data == model_serialized

    def test_update_view_wrong_user_id(
        self, two_retina_polygon_annotation_sets, rf, user_type
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
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first(),
            rf,
            SinglePolygonViewSet,
            model_json,
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
        self, two_retina_polygon_annotation_sets, rf, user_type
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
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first(),
            rf,
            SinglePolygonViewSet,
            model_json,
        )

        if user_type in ("retina_grader", "retina_admin"):
            assert response.data == model_serialized

    def test_destroy_view(
        self, two_retina_polygon_annotation_sets, rf, user_type
    ):
        view_test(
            "destroy",
            user_type,
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader1,
            two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first(),
            rf,
            SinglePolygonViewSet,
        )
        if user_type in ("retina_grader", "retina_admin"):
            assert not PolygonAnnotationSet.objects.filter(
                id=two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first().id
            ).exists()

    def test_destroy_view_wrong_user(
        self, two_retina_polygon_annotation_sets, rf, user_type
    ):
        response = view_test(
            "destroy",
            user_type,
            self.namespace,
            self.basename,
            two_retina_polygon_annotation_sets.grader2,
            two_retina_polygon_annotation_sets.polygonset1.singlepolygonannotation_set.first(),
            rf,
            SinglePolygonViewSet,
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
class TestGradersWithPolygonAnnotationsListView(TestCase):
    def setUp(self):
        self.annotation_set = generate_two_polygon_annotation_sets(
            retina_grader=True
        )
        self.kwargs = {"image_id": self.annotation_set.polygonset1.image.id}
        self.url = reverse(
            "retina:api:polygon-annotation-users-list-view", kwargs=self.kwargs
        )
        self.view = GradersWithPolygonAnnotationsListView.as_view()
        self.rf = APIRequestFactory()
        self.request = self.rf.get(self.url)
        self.retina_admin = UserFactory()
        self.retina_admin.groups.add(
            Group.objects.get(name=settings.RETINA_ADMINS_GROUP_NAME)
        )

    def test_non_authenticated(self):
        response = self.view(self.request, **self.kwargs)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_non_retina_user(self):
        self.annotation_set.polygonset1.grader.groups.clear()
        force_authenticate(
            self.request, user=self.annotation_set.polygonset1.grader
        )
        response = self.view(self.request, **self.kwargs)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retina_grader(self):
        force_authenticate(
            self.request, user=self.annotation_set.polygonset1.grader
        )
        response = self.view(self.request, **self.kwargs)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_authenticated(self):
        force_authenticate(self.request, user=self.retina_admin)
        response = self.view(self.request, **self.kwargs)

        assert response.status_code == status.HTTP_200_OK
        assert (
            response.data[0]
            == UserSerializer(
                instance=self.annotation_set.polygonset1.grader
            ).data
        )

    def test_multiple_graders(self):
        graders = (
            UserFactory(),
            UserFactory(),
            UserFactory(),
            UserFactory(),
            UserFactory(),
        )
        polygon_sets = [self.annotation_set.polygonset1]
        for grader in graders:
            grader.groups.add(
                Group.objects.get(name=settings.RETINA_GRADERS_GROUP_NAME)
            )
            polygon_sets.append(
                PolygonAnnotationSetFactory(
                    grader=grader, image=self.annotation_set.polygonset1.image
                )
            )

        force_authenticate(self.request, user=self.retina_admin)
        response = self.view(self.request, **self.kwargs)

        graders = get_user_model().objects.filter(
            polygonannotationset__in=polygon_sets
        )
        expected_response = UserSerializer(graders, many=True).data
        expected_response.sort(key=lambda k: k["id"])

        assert response.status_code == status.HTTP_200_OK
        response.data.sort(key=lambda k: k["id"])
        assert response.data == expected_response

    def test_multiple_graders_some_retina_grader(self):
        graders = (
            UserFactory(),
            UserFactory(),
            UserFactory(),
            UserFactory(),
            UserFactory(),
        )
        polygon_sets = [self.annotation_set.polygonset1]
        for index, grader in enumerate(graders):
            if index % 2 == 0:
                grader.groups.add(
                    Group.objects.get(name=settings.RETINA_GRADERS_GROUP_NAME)
                )
            polygon_sets.append(
                PolygonAnnotationSetFactory(
                    grader=grader, image=self.annotation_set.polygonset1.image
                )
            )

        force_authenticate(self.request, user=self.retina_admin)
        response = self.view(self.request, **self.kwargs)

        graders = get_user_model().objects.filter(
            polygonannotationset__in=polygon_sets,
            groups__name=settings.RETINA_GRADERS_GROUP_NAME,
        )
        expected_response = UserSerializer(graders, many=True).data
        expected_response.sort(key=lambda k: k["id"])

        assert response.status_code == status.HTTP_200_OK
        response.data.sort(key=lambda k: k["id"])
        assert response.data == expected_response

    def test_multiple_polygonsets_for_one_grader_distinct(self):
        grader = UserFactory()
        grader.groups.add(
            Group.objects.get(name=settings.RETINA_GRADERS_GROUP_NAME)
        )
        polygon_sets = [
            self.annotation_set.polygonset1,
            PolygonAnnotationSetFactory(
                grader=grader, image=self.annotation_set.polygonset1.image
            ),
            PolygonAnnotationSetFactory(
                grader=grader, image=self.annotation_set.polygonset1.image
            ),
        ]

        force_authenticate(self.request, user=self.retina_admin)
        response = self.view(self.request, **self.kwargs)

        graders = (
            get_user_model()
            .objects.filter(
                polygonannotationset__in=polygon_sets,
                groups__name=settings.RETINA_GRADERS_GROUP_NAME,
            )
            .distinct()
        )
        expected_response = UserSerializer(graders, many=True).data
        expected_response.sort(key=lambda k: k["id"])

        assert response.status_code == status.HTTP_200_OK
        response.data.sort(key=lambda k: k["id"])
        assert response.data == expected_response


@pytest.mark.django_db
class TestLandmarkAnnotationSetForImageListListView(TestCase):
    def setUp(self):
        self.annotation_set = generate_multiple_landmark_annotation_sets(
            retina_grader=True
        )
        self.kwargs = {"user_id": self.annotation_set.landmarkset1.grader.id}
        list_of_image_ids = list(
            map(lambda x: str(x.id), self.annotation_set.landmarkset1images)
        )
        self.url_no_params = reverse(
            "retina:api:landmark-annotation-images-list-view",
            kwargs=self.kwargs,
        )
        self.url = "{}?image_ids={}".format(
            self.url_no_params, ",".join(list_of_image_ids)
        )
        self.view = LandmarkAnnotationSetForImageList.as_view()
        self.rf = APIRequestFactory()
        self.request = self.rf.get(self.url)
        self.retina_admin = UserFactory()
        self.retina_admin.groups.add(
            Group.objects.get(name=settings.RETINA_ADMINS_GROUP_NAME)
        )

    def test_non_authenticated(self):
        response = self.view(self.request, **self.kwargs)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_non_retina_user(self):
        self.annotation_set.landmarkset1.grader.groups.clear()
        force_authenticate(
            self.request, user=self.annotation_set.landmarkset1.grader
        )
        response = self.view(self.request, **self.kwargs)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retina_grader_no_params(self):
        request = self.rf.get(self.url_no_params)
        force_authenticate(
            request, user=self.annotation_set.landmarkset1.grader
        )
        response = self.view(request, **self.kwargs)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retina_grader_empty(self):
        list_of_image_ids = list(
            map(lambda x: str(x.id), self.annotation_set.landmarkset2images)
        )
        url = "{}?image_ids={}".format(
            self.url_no_params, ",".join(list_of_image_ids)
        )
        request = self.rf.get(url)
        force_authenticate(
            request, user=self.annotation_set.landmarkset1.grader
        )
        response = self.view(request, **self.kwargs)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    def test_retina_grader_one_set(self):
        kwargs = {"user_id": self.annotation_set.landmarkset2.grader.id}
        url_no_params = reverse(
            "retina:api:landmark-annotation-images-list-view", kwargs=kwargs
        )
        url = "{}?image_ids={}".format(
            url_no_params, self.annotation_set.landmarkset2images[0].id
        )
        request = self.rf.get(url)
        force_authenticate(
            request, user=self.annotation_set.landmarkset2.grader
        )
        response = self.view(request, **kwargs)
        expected_response = [
            LandmarkAnnotationSetSerializer(
                instance=self.annotation_set.landmarkset2
            ).data
        ]

        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected_response

    def test_retina_grader_both_sets(self):
        force_authenticate(
            self.request, user=self.annotation_set.landmarkset1.grader
        )
        response = self.view(self.request, **self.kwargs)
        expected_response = LandmarkAnnotationSetSerializer(
            [
                self.annotation_set.landmarkset1,
                self.annotation_set.landmarkset3,
            ],
            many=True,
        ).data
        expected_response.sort(key=lambda k: k["id"])

        assert response.status_code == status.HTTP_200_OK
        response.data.sort(key=lambda k: k["id"])
        assert response.data == expected_response

    def test_admin_authenticated(self):
        force_authenticate(self.request, user=self.retina_admin)
        response = self.view(self.request, **self.kwargs)

        expected_response = LandmarkAnnotationSetSerializer(
            [
                self.annotation_set.landmarkset1,
                self.annotation_set.landmarkset3,
            ],
            many=True,
        ).data
        expected_response.sort(key=lambda k: k["id"])

        assert response.status_code == status.HTTP_200_OK
        response.data.sort(key=lambda k: k["id"])
        assert response.data == expected_response


@pytest.mark.django_db
class TestOctObsRegistrationRetrieveView(TestCase):
    def setUp(self):
        self.octobsregistration = OctObsRegistrationFactory()
        self.kwargs = {"image_id": self.octobsregistration.obs_image.id}
        self.url = reverse(
            "retina:api:octobs-registration-detail-view", kwargs=self.kwargs
        )
        self.view = OctObsRegistrationRetrieve.as_view()
        self.rf = APIRequestFactory()
        self.request = self.rf.get(self.url)

        self.retina_user = UserFactory()
        self.retina_user.groups.add(
            Group.objects.get(name=settings.RETINA_GRADERS_GROUP_NAME)
        )

    def test_non_authenticated(self):
        response = self.view(self.request, **self.kwargs)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_non_retina_user(self):
        user = UserFactory()
        force_authenticate(self.request, user=user)
        response = self.view(self.request, **self.kwargs)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retina_user_non_existant_image(self):
        image = self.octobsregistration.obs_image
        kwargs = {"image_id": image.id}
        url = reverse(
            "retina:api:octobs-registration-detail-view", kwargs=kwargs
        )
        request = self.rf.get(url)
        force_authenticate(request, user=self.retina_user)
        image.delete()
        response = self.view(request, **kwargs)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retina_user_no_registration(self):
        image = ImageFactory()
        kwargs = {"image_id": image.id}
        url = reverse(
            "retina:api:octobs-registration-detail-view", kwargs=kwargs
        )
        request = self.rf.get(url)
        force_authenticate(request, user=self.retina_user)
        response = self.view(request, **kwargs)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retina_user_get_via_obs_image(self):
        force_authenticate(self.request, user=self.retina_user)
        response = self.view(self.request, **self.kwargs)

        expected_response = OctObsRegistrationSerializer(
            instance=self.octobsregistration
        ).data

        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected_response

    def test_retina_user_get_via_oct_image(self):
        image = self.octobsregistration.oct_image
        kwargs = {"image_id": image.id}
        url = reverse(
            "retina:api:octobs-registration-detail-view", kwargs=kwargs
        )
        request = self.rf.get(url)
        force_authenticate(request, user=self.retina_user)
        response = self.view(request, **kwargs)

        expected_response = OctObsRegistrationSerializer(
            instance=self.octobsregistration
        ).data

        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected_response

    def test_admin_user_get_via_obs_image(self):
        retina_admin = UserFactory()
        retina_admin.groups.add(
            Group.objects.get(name=settings.RETINA_ADMINS_GROUP_NAME)
        )
        force_authenticate(self.request, user=retina_admin)
        response = self.view(self.request, **self.kwargs)

        expected_response = OctObsRegistrationSerializer(
            instance=self.octobsregistration
        ).data

        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected_response


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
class TestETDRSAnnotationViewSet:
    namespace = "retina:api"
    basename = "etdrsgridannotation"

    def test_list_view(self, multiple_retina_etdrs_annotations, rf, user_type):
        response = view_test(
            "list",
            user_type,
            self.namespace,
            self.basename,
            multiple_retina_etdrs_annotations.grader1,
            None,
            rf,
            ETDRSGridAnnotationViewSet,
        )
        if user_type == "retina_grader":
            serialized_data = ETDRSGridAnnotationSerializer(
                multiple_retina_etdrs_annotations.etdrss1, many=True
            ).data
            assert len(response.data) == len(serialized_data)
            serialized_data.sort(key=lambda k: k["created"], reverse=True)
            assert response.data == serialized_data
        elif user_type == "retina_admin":
            serialized_data = ETDRSGridAnnotationSerializer(
                [
                    *multiple_retina_etdrs_annotations.etdrss1,
                    *multiple_retina_etdrs_annotations.etdrss2,
                ],
                many=True,
            ).data
            serialized_data.sort(key=lambda k: k["created"], reverse=True)
            assert len(response.data) == len(serialized_data)
            assert response.data == serialized_data

    def test_create_view(
        self, multiple_retina_etdrs_annotations, rf, user_type
    ):
        model_build = ETDRSGridAnnotationFactory.build(
            grader=multiple_retina_etdrs_annotations.grader1,
            image=multiple_retina_etdrs_annotations.etdrss1[0].image,
        )
        model_serialized = ETDRSGridAnnotationSerializer(model_build).data
        model_serialized[
            "grader"
        ] = multiple_retina_etdrs_annotations.grader1.id
        model_serialized["image"] = str(model_serialized["image"])
        model_json = json.dumps(model_serialized)

        response = view_test(
            "create",
            user_type,
            self.namespace,
            self.basename,
            multiple_retina_etdrs_annotations.grader1,
            None,
            rf,
            ETDRSGridAnnotationViewSet,
            model_json,
        )
        if user_type in ("retina_grader", "retina_admin"):
            model_serialized["id"] = response.data["id"]
            response.data["image"] = str(response.data["image"])
            assert response.data == model_serialized

    def test_create_view_no_od(
        self, multiple_retina_etdrs_annotations, rf, user_type
    ):
        model_build = ETDRSGridAnnotationFactory.build(
            grader=multiple_retina_etdrs_annotations.grader1,
            image=multiple_retina_etdrs_annotations.etdrss1[0].image,
        )
        model_serialized = ETDRSGridAnnotationSerializer(model_build).data
        model_serialized[
            "grader"
        ] = multiple_retina_etdrs_annotations.grader1.id
        model_serialized["image"] = str(model_serialized["image"])
        model_serialized["optic_disk"] = []
        model_json = json.dumps(model_serialized)

        response = view_test(
            "create",
            user_type,
            self.namespace,
            self.basename,
            multiple_retina_etdrs_annotations.grader1,
            None,
            rf,
            ETDRSGridAnnotationViewSet,
            model_json,
        )
        if user_type in ("retina_grader", "retina_admin"):
            model_serialized["id"] = response.data["id"]
            response.data["image"] = str(response.data["image"])
            assert response.data == model_serialized

    def test_create_view_wrong_user_id(
        self, multiple_retina_etdrs_annotations, rf, user_type
    ):
        other_user = UserFactory()
        model_build = ETDRSGridAnnotationFactory.build(
            grader=other_user,
            image=multiple_retina_etdrs_annotations.etdrss1[0].image,
        )
        model_serialized = ETDRSGridAnnotationSerializer(model_build).data
        model_serialized[
            "grader"
        ] = multiple_retina_etdrs_annotations.grader2.id
        model_serialized["image"] = str(model_serialized["image"])
        model_json = json.dumps(model_serialized)

        response = view_test(
            "create",
            user_type,
            self.namespace,
            self.basename,
            multiple_retina_etdrs_annotations.grader1,
            None,
            rf,
            ETDRSGridAnnotationViewSet,
            model_json,
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
        self, multiple_retina_etdrs_annotations, rf, user_type
    ):
        response = view_test(
            "retrieve",
            user_type,
            self.namespace,
            self.basename,
            multiple_retina_etdrs_annotations.grader1,
            multiple_retina_etdrs_annotations.etdrss1[0],
            rf,
            ETDRSGridAnnotationViewSet,
        )
        if user_type == "retina_grader" or user_type == "retina_admin":
            model_serialized = ETDRSGridAnnotationSerializer(
                multiple_retina_etdrs_annotations.etdrss1[0]
            ).data
            assert response.data == model_serialized

    def test_update_view(
        self, multiple_retina_etdrs_annotations, rf, user_type
    ):
        model_serialized = ETDRSGridAnnotationSerializer(
            multiple_retina_etdrs_annotations.etdrss1[0]
        ).data
        model_serialized["image"] = str(model_serialized["image"])
        model_serialized["fovea"] = [123, 456]
        model_json = json.dumps(model_serialized)

        response = view_test(
            "update",
            user_type,
            self.namespace,
            self.basename,
            multiple_retina_etdrs_annotations.grader1,
            multiple_retina_etdrs_annotations.etdrss1[0],
            rf,
            ETDRSGridAnnotationViewSet,
            model_json,
        )

        if user_type in ("retina_grader", "retina_admin"):
            response.data["image"] = str(response.data["image"])
            assert response.data == model_serialized

    def test_update_view_wrong_user_id(
        self, multiple_retina_etdrs_annotations, rf, user_type
    ):
        model_serialized = ETDRSGridAnnotationSerializer(
            multiple_retina_etdrs_annotations.etdrss1[0]
        ).data
        other_user = UserFactory()
        model_serialized["grader"] = other_user.id
        model_serialized["image"] = str(model_serialized["image"])
        model_json = json.dumps(model_serialized)

        response = view_test(
            "update",
            user_type,
            self.namespace,
            self.basename,
            multiple_retina_etdrs_annotations.grader1,
            multiple_retina_etdrs_annotations.etdrss1[0],
            rf,
            ETDRSGridAnnotationViewSet,
            model_json,
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
        self, multiple_retina_etdrs_annotations, rf, user_type
    ):
        model_serialized = ETDRSGridAnnotationSerializer(
            multiple_retina_etdrs_annotations.etdrss1[0]
        ).data
        partial_model = copy.deepcopy(model_serialized)
        del partial_model["image"]
        del partial_model["id"]
        del partial_model["grader"]
        del partial_model["optic_disk"]
        model_json = json.dumps(partial_model)

        response = view_test(
            "partial_update",
            user_type,
            self.namespace,
            self.basename,
            multiple_retina_etdrs_annotations.grader1,
            multiple_retina_etdrs_annotations.etdrss1[0],
            rf,
            ETDRSGridAnnotationViewSet,
            model_json,
        )

        if user_type in ("retina_grader", "retina_admin"):
            assert response.data == model_serialized

    def test_destroy_view(
        self, multiple_retina_etdrs_annotations, rf, user_type
    ):
        view_test(
            "destroy",
            user_type,
            self.namespace,
            self.basename,
            multiple_retina_etdrs_annotations.grader1,
            multiple_retina_etdrs_annotations.etdrss1[0],
            rf,
            ETDRSGridAnnotationViewSet,
        )
        if user_type in ("retina_grader", "retina_admin"):
            assert not ETDRSGridAnnotation.objects.filter(
                id=multiple_retina_etdrs_annotations.etdrss1[0].id
            ).exists()

    def test_destroy_view_wrong_user(
        self, multiple_retina_etdrs_annotations, rf, user_type
    ):
        response = view_test(
            "destroy",
            user_type,
            self.namespace,
            self.basename,
            multiple_retina_etdrs_annotations.grader2,
            multiple_retina_etdrs_annotations.etdrss1[0],
            rf,
            ETDRSGridAnnotationViewSet,
            check_response_status_code=False,
        )
        if user_type == "retina_admin":
            assert not ETDRSGridAnnotation.objects.filter(
                id=multiple_retina_etdrs_annotations.etdrss1[0].id
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
    "viewset,factory,serializer",
    (
        (
            ImageQualityAnnotationViewSet,
            ImageQualityAnnotationFactory,
            ImageQualityAnnotationSerializer,
        ),
        (
            ImagePathologyAnnotationViewSet,
            ImagePathologyAnnotationFactory,
            ImagePathologyAnnotationSerializer,
        ),
        (
            RetinaImagePathologyAnnotationViewSet,
            RetinaImagePathologyAnnotationFactory,
            RetinaImagePathologyAnnotationSerializer,
        ),
        (
            ImageTextAnnotationViewSet,
            ImageTextAnnotationFactory,
            ImageTextAnnotationSerializer,
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

    def test_list_view(self, rf, user_type, viewset, factory, serializer):
        models = self.create_models(factory)
        response = view_test(
            "list",
            user_type,
            self.namespace,
            factory._meta.model._meta.model_name,
            models[0].grader,
            None,
            rf,
            viewset,
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

    def test_create_view(self, rf, user_type, viewset, factory, serializer):
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
            self.namespace,
            factory._meta.model._meta.model_name,
            models[0].grader,
            None,
            rf,
            viewset,
            model_json,
        )
        if user_type in ("retina_grader", "retina_admin"):
            model_serialized["id"] = response.data["id"]
            response.data["image"] = str(response.data["image"])
            assert response.data == model_serialized

    def test_create_view_wrong_user_id(
        self, rf, user_type, viewset, factory, serializer
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
            self.namespace,
            factory._meta.model._meta.model_name,
            models[0].grader,
            None,
            rf,
            viewset,
            model_json,
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

    def test_retrieve_view(self, rf, user_type, viewset, factory, serializer):
        models = self.create_models(factory)
        response = view_test(
            "retrieve",
            user_type,
            self.namespace,
            factory._meta.model._meta.model_name,
            models[0].grader,
            models[0],
            rf,
            viewset,
        )
        if user_type == "retina_grader" or user_type == "retina_admin":
            model_serialized = serializer(models[0]).data
            assert response.data == model_serialized

    def test_update_view(self, rf, user_type, viewset, factory, serializer):
        models = self.create_models(factory)
        model_serialized = serializer(models[1]).data
        models[1].delete()
        model_serialized["image"] = str(model_serialized["image"])
        model_serialized["id"] = str(models[0].id)
        model_json = json.dumps(model_serialized)

        response = view_test(
            "update",
            user_type,
            self.namespace,
            factory._meta.model._meta.model_name,
            models[0].grader,
            models[0],
            rf,
            viewset,
            model_json,
        )

        if user_type in ("retina_grader", "retina_admin"):
            response.data["image"] = str(response.data["image"])
            assert response.data == model_serialized

    def test_update_view_wrong_user_id(
        self, rf, user_type, viewset, factory, serializer
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
            self.namespace,
            factory._meta.model._meta.model_name,
            models[0].grader,
            models[0],
            rf,
            viewset,
            model_json,
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
        self, rf, user_type, viewset, factory, serializer
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
            self.namespace,
            factory._meta.model._meta.model_name,
            models[0].grader,
            models[0],
            rf,
            viewset,
            model_json,
        )

        if user_type in ("retina_grader", "retina_admin"):
            assert response.data == model_serialized

    def test_destroy_view(self, rf, user_type, viewset, factory, serializer):
        models = self.create_models(factory)
        view_test(
            "destroy",
            user_type,
            self.namespace,
            factory._meta.model._meta.model_name,
            models[0].grader,
            models[0],
            rf,
            viewset,
        )
        if user_type in ("retina_grader", "retina_admin"):
            assert not factory._meta.model.objects.filter(
                id=models[0].id
            ).exists()

    def test_destroy_view_wrong_user(
        self, rf, user_type, viewset, factory, serializer
    ):
        models = self.create_models(factory)
        response = view_test(
            "destroy",
            user_type,
            self.namespace,
            factory._meta.model._meta.model_name,
            models[2].grader,
            models[0],
            rf,
            viewset,
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
            "landmark-annotation",
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

        url = reverse(f"api:landmark-annotation-list") + querystring

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
            rf, user_type, f"?image_id=invalid_uuid"
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
