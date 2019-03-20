import json
import pytest

from rest_framework import status
from django.test import TestCase
from django.contrib.auth.models import Group
from rest_framework.test import force_authenticate, APIRequestFactory
from grandchallenge.subdomains.utils import reverse
from django.conf import settings
from django.contrib.auth import get_user_model

from tests.cases_tests.factories import ImageFactory
from tests.factories import UserFactory
from tests.annotations_tests.factories import (
    PolygonAnnotationSetFactory,
    SinglePolygonAnnotationFactory,
)
from grandchallenge.annotations.serializers import (
    PolygonAnnotationSetSerializer,
    SinglePolygonAnnotationSerializer,
)
from grandchallenge.core.serializers import UserSerializer
from grandchallenge.annotations.models import PolygonAnnotationSet
from grandchallenge.retina_api.views import (
    PolygonAnnotationSetViewSet,
    SinglePolygonViewSet,
    PolygonListView,
    GradersWithPolygonAnnotationsListView,
)
from tests.conftest import (
    generate_annotation_set,
    generate_two_polygon_annotation_sets,
)
from tests.viewset_helpers import view_test


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

    def test_list_view(self, TwoRetinaPolygonAnnotationSets, rf, user_type):
        response = view_test(
            "list",
            user_type,
            self.namespace,
            self.basename,
            TwoRetinaPolygonAnnotationSets.grader1,
            TwoRetinaPolygonAnnotationSets.polygonset1,
            rf,
            PolygonAnnotationSetViewSet,
        )
        if user_type in ("retina_grader", "retina_admin"):
            serialized_data = PolygonAnnotationSetSerializer(
                TwoRetinaPolygonAnnotationSets.polygonset1
            ).data
            assert response.data[0] == serialized_data

    def test_create_view(self, TwoRetinaPolygonAnnotationSets, rf, user_type):
        model_build = PolygonAnnotationSetFactory.build()
        model_serialized = PolygonAnnotationSetSerializer(model_build).data
        image = ImageFactory()
        model_serialized["image"] = str(image.id)
        model_serialized["grader"] = TwoRetinaPolygonAnnotationSets.grader1.id
        model_json = json.dumps(model_serialized)

        response = view_test(
            "create",
            user_type,
            self.namespace,
            self.basename,
            TwoRetinaPolygonAnnotationSets.grader1,
            TwoRetinaPolygonAnnotationSets.polygonset1,
            rf,
            PolygonAnnotationSetViewSet,
            model_json,
        )
        if user_type in ("retina_grader", "retina_admin"):
            model_serialized["id"] = response.data["id"]
            response.data["image"] = str(response.data["image"])
            assert response.data == model_serialized

    def test_create_view_wrong_user_id(
        self, TwoRetinaPolygonAnnotationSets, rf, user_type
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
            TwoRetinaPolygonAnnotationSets.grader1,
            TwoRetinaPolygonAnnotationSets.polygonset1,
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
        self, TwoRetinaPolygonAnnotationSets, rf, user_type
    ):
        response = view_test(
            "retrieve",
            user_type,
            self.namespace,
            self.basename,
            TwoRetinaPolygonAnnotationSets.grader1,
            TwoRetinaPolygonAnnotationSets.polygonset1,
            rf,
            PolygonAnnotationSetViewSet,
        )
        if user_type == "retina_grader" or user_type == "retina_admin":
            model_serialized = PolygonAnnotationSetSerializer(
                instance=TwoRetinaPolygonAnnotationSets.polygonset1
            ).data
            assert response.data == model_serialized

    def test_update_view(self, TwoRetinaPolygonAnnotationSets, rf, user_type):
        model_serialized = PolygonAnnotationSetSerializer(
            instance=TwoRetinaPolygonAnnotationSets.polygonset1
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
            TwoRetinaPolygonAnnotationSets.grader1,
            TwoRetinaPolygonAnnotationSets.polygonset1,
            rf,
            PolygonAnnotationSetViewSet,
            model_json,
        )

        if user_type in ("retina_grader", "retina_admin"):
            response.data["image"] = str(response.data["image"])
            response.data["singlepolygonannotation_set"] = []
            assert response.data == model_serialized

    def test_update_view_wrong_user(
        self, TwoRetinaPolygonAnnotationSets, rf, user_type
    ):
        model_serialized = PolygonAnnotationSetSerializer(
            instance=TwoRetinaPolygonAnnotationSets.polygonset1
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
            TwoRetinaPolygonAnnotationSets.grader1,
            TwoRetinaPolygonAnnotationSets.polygonset1,
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
        self, TwoRetinaPolygonAnnotationSets, rf, user_type
    ):
        model_serialized = PolygonAnnotationSetSerializer(
            instance=TwoRetinaPolygonAnnotationSets.polygonset1
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
            TwoRetinaPolygonAnnotationSets.grader1,
            TwoRetinaPolygonAnnotationSets.polygonset1,
            rf,
            PolygonAnnotationSetViewSet,
            model_json,
        )

        if user_type in ("retina_grader", "retina_admin"):
            response.data["image"] = str(response.data["image"])
            response.data["singlepolygonannotation_set"] = []
            assert response.data == model_serialized

    def test_destroy_view(self, TwoRetinaPolygonAnnotationSets, rf, user_type):
        view_test(
            "destroy",
            user_type,
            self.namespace,
            self.basename,
            TwoRetinaPolygonAnnotationSets.grader1,
            TwoRetinaPolygonAnnotationSets.polygonset1,
            rf,
            PolygonAnnotationSetViewSet,
        )
        if user_type in ("retina_grader", "retina_admin"):
            assert not PolygonAnnotationSet.objects.filter(
                id=TwoRetinaPolygonAnnotationSets.polygonset1.id
            ).exists()

    def test_destroy_view_wrong_user(
        self, TwoRetinaPolygonAnnotationSets, rf, user_type
    ):
        response = view_test(
            "destroy",
            user_type,
            self.namespace,
            self.basename,
            TwoRetinaPolygonAnnotationSets.grader1,
            TwoRetinaPolygonAnnotationSets.polygonset2,
            rf,
            PolygonAnnotationSetViewSet,
            check_response_status_code=False,
        )
        if user_type == "retina_admin":
            assert not PolygonAnnotationSet.objects.filter(
                id=TwoRetinaPolygonAnnotationSets.polygonset2.id
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

    def test_list_view(self, TwoRetinaPolygonAnnotationSets, rf, user_type):
        response = view_test(
            "list",
            user_type,
            self.namespace,
            self.basename,
            TwoRetinaPolygonAnnotationSets.grader1,
            None,
            rf,
            SinglePolygonViewSet,
        )
        if user_type == "retina_grader":
            serialized_data = SinglePolygonAnnotationSerializer(
                TwoRetinaPolygonAnnotationSets.polygonset1.singlepolygonannotation_set.all(),
                many=True,
            ).data
            assert len(response.data) == len(serialized_data)
            response.data.sort(key=lambda k: k["id"])
            serialized_data.sort(key=lambda k: k["id"])
            assert response.data == serialized_data
        elif user_type == "retina_admin":
            serialized_data = SinglePolygonAnnotationSerializer(
                TwoRetinaPolygonAnnotationSets.polygonset1.singlepolygonannotation_set.all()
                | TwoRetinaPolygonAnnotationSets.polygonset2.singlepolygonannotation_set.all(),
                many=True,
            ).data
            assert response.data == serialized_data

    def test_create_view(self, TwoRetinaPolygonAnnotationSets, rf, user_type):
        model_build = SinglePolygonAnnotationFactory.build()
        model_serialized = SinglePolygonAnnotationSerializer(model_build).data
        annotation_set = PolygonAnnotationSetFactory(
            grader=TwoRetinaPolygonAnnotationSets.grader1
        )
        model_serialized["annotation_set"] = str(annotation_set.id)
        model_json = json.dumps(model_serialized)

        response = view_test(
            "create",
            user_type,
            self.namespace,
            self.basename,
            TwoRetinaPolygonAnnotationSets.grader1,
            None,
            rf,
            SinglePolygonViewSet,
            model_json,
        )
        if user_type in ("retina_grader", "retina_admin"):
            model_serialized["id"] = response.data["id"]
            response.data["annotation_set"] = str(
                response.data["annotation_set"]
            )
            assert response.data == model_serialized

    def test_create_view_wrong_user_id(
        self, TwoRetinaPolygonAnnotationSets, rf, user_type
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
            TwoRetinaPolygonAnnotationSets.grader1,
            None,
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

    def test_retrieve_view(
        self, TwoRetinaPolygonAnnotationSets, rf, user_type
    ):
        response = view_test(
            "retrieve",
            user_type,
            self.namespace,
            self.basename,
            TwoRetinaPolygonAnnotationSets.grader1,
            TwoRetinaPolygonAnnotationSets.polygonset1.singlepolygonannotation_set.first(),
            rf,
            SinglePolygonViewSet,
        )
        if user_type == "retina_grader" or user_type == "retina_admin":
            model_serialized = SinglePolygonAnnotationSerializer(
                TwoRetinaPolygonAnnotationSets.polygonset1.singlepolygonannotation_set.first()
            ).data
            assert response.data == model_serialized

    def test_update_view(self, TwoRetinaPolygonAnnotationSets, rf, user_type):
        model_serialized = SinglePolygonAnnotationSerializer(
            TwoRetinaPolygonAnnotationSets.polygonset1.singlepolygonannotation_set.first()
        ).data
        annotation_set = PolygonAnnotationSetFactory(
            grader=TwoRetinaPolygonAnnotationSets.grader1
        )
        model_serialized["annotation_set"] = str(annotation_set.id)
        model_json = json.dumps(model_serialized)

        response = view_test(
            "update",
            user_type,
            self.namespace,
            self.basename,
            TwoRetinaPolygonAnnotationSets.grader1,
            TwoRetinaPolygonAnnotationSets.polygonset1.singlepolygonannotation_set.first(),
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
        self, TwoRetinaPolygonAnnotationSets, rf, user_type
    ):
        model_serialized = SinglePolygonAnnotationSerializer(
            TwoRetinaPolygonAnnotationSets.polygonset1.singlepolygonannotation_set.first()
        ).data
        annotation_set = PolygonAnnotationSetFactory()
        model_serialized["annotation_set"] = str(annotation_set.id)
        model_json = json.dumps(model_serialized)

        response = view_test(
            "update",
            user_type,
            self.namespace,
            self.basename,
            TwoRetinaPolygonAnnotationSets.grader1,
            TwoRetinaPolygonAnnotationSets.polygonset1.singlepolygonannotation_set.first(),
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
        self, TwoRetinaPolygonAnnotationSets, rf, user_type
    ):
        model_serialized = SinglePolygonAnnotationSerializer(
            TwoRetinaPolygonAnnotationSets.polygonset1.singlepolygonannotation_set.first()
        ).data
        annotation_set = PolygonAnnotationSetFactory(
            grader=TwoRetinaPolygonAnnotationSets.grader1
        )
        model_serialized["annotation_set"] = str(annotation_set.id)
        model_json = json.dumps(model_serialized)

        response = view_test(
            "partial_update",
            user_type,
            self.namespace,
            self.basename,
            TwoRetinaPolygonAnnotationSets.grader1,
            TwoRetinaPolygonAnnotationSets.polygonset1.singlepolygonannotation_set.first(),
            rf,
            SinglePolygonViewSet,
            model_json,
        )

        if user_type in ("retina_grader", "retina_admin"):
            response.data["annotation_set"] = str(
                response.data["annotation_set"]
            )
            assert response.data == model_serialized

    def test_destroy_view(self, TwoRetinaPolygonAnnotationSets, rf, user_type):
        view_test(
            "destroy",
            user_type,
            self.namespace,
            self.basename,
            TwoRetinaPolygonAnnotationSets.grader1,
            TwoRetinaPolygonAnnotationSets.polygonset1.singlepolygonannotation_set.first(),
            rf,
            SinglePolygonViewSet,
        )
        if user_type in ("retina_grader", "retina_admin"):
            assert not PolygonAnnotationSet.objects.filter(
                id=TwoRetinaPolygonAnnotationSets.polygonset1.singlepolygonannotation_set.first().id
            ).exists()

    def test_destroy_view_wrong_user(
        self, TwoRetinaPolygonAnnotationSets, rf, user_type
    ):
        response = view_test(
            "destroy",
            user_type,
            self.namespace,
            self.basename,
            TwoRetinaPolygonAnnotationSets.grader2,
            TwoRetinaPolygonAnnotationSets.polygonset1.singlepolygonannotation_set.first(),
            rf,
            SinglePolygonViewSet,
            check_response_status_code=False,
        )
        if user_type == "retina_admin":
            assert not PolygonAnnotationSet.objects.filter(
                id=TwoRetinaPolygonAnnotationSets.polygonset1.singlepolygonannotation_set.first().id
            ).exists()
        elif user_type == "retina_grader":
            assert response.status_code == status.HTTP_404_NOT_FOUND
        else:
            assert response.status_code == status.HTTP_403_FORBIDDEN


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
