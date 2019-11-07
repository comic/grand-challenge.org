import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse as django_reverse
from rest_framework import status

from grandchallenge.subdomains.utils import reverse
from tests.annotations_tests.factories import (
    BooleanClassificationAnnotationFactory,
    ETDRSGridAnnotationFactory,
    LandmarkAnnotationSetFactory,
    MeasurementAnnotationFactory,
    PolygonAnnotationSetFactory,
    SingleLandmarkAnnotationFactory,
    SinglePolygonAnnotationFactory,
)
from tests.cases_tests.factories import ImageFactory
from tests.factories import UserFactory
from tests.registrations_tests.factories import OctObsRegistrationFactory
from tests.retina_core_tests.factories import create_some_datastructure_data
from tests.retina_importers_tests.helpers import get_retina_user_with_token
from tests.viewset_helpers import TEST_USER_CREDENTIALS


def get_user_from_str(user=None):
    try:
        return get_user_model().objects.get(
            username=TEST_USER_CREDENTIALS["username"]
        )
    except get_user_model().DoesNotExist:
        if user == "staff":
            user = get_user_model().objects.create_superuser(
                **TEST_USER_CREDENTIALS
            )
        elif user == "retina_user":
            user = get_user_model().objects.create_user(
                **TEST_USER_CREDENTIALS
            )
            grader_group, group_created = Group.objects.get_or_create(
                name=settings.RETINA_GRADERS_GROUP_NAME
            )
            grader_group.user_set.add(user)
        elif user == "normal":
            user = get_user_model().objects.create_user(
                **TEST_USER_CREDENTIALS
            )
        return user


def client_login(client, user=None):
    user = get_user_from_str(user)
    if user is not None and not isinstance(user, str):
        client.login(**TEST_USER_CREDENTIALS)
    return client, user


def client_force_login(client, user=None):
    user = get_user_from_str(user)
    if user is not None and not isinstance(user, str):
        client.force_login(user=user)
    return client, user


def create_datastructures_data():
    datastructures = create_some_datastructure_data()
    datastructures_aus = create_some_datastructure_data(
        archive_pars={"name": "Australia"}
    )
    oct_obs_registration_aus = OctObsRegistrationFactory(
        oct_image=datastructures_aus["image_oct"],
        obs_image=datastructures_aus["image_obs"],
    )
    oct_obs_registration = OctObsRegistrationFactory(
        oct_image=datastructures["image_oct"],
        obs_image=datastructures["image_obs"],
    )
    return (
        datastructures,
        datastructures_aus,
        oct_obs_registration,
        oct_obs_registration_aus,
    )


def batch_test_image_endpoint_redirects(test_class):
    for image_type, reverse_name in (
        ("thumb", "retina:image-thumbnail"),
        ("original", "retina:image-numpy"),
    ):
        (
            test_redirect_no_perm,
            test_redirect,
            test_redirect_australia,
            test_redirect_kappa,
            test_redirect_oct,
        ) = create_image_test_method(image_type, reverse_name)
        test_redirect_no_perm.__name__ = (
            f"test_image_{image_type}_redirect_no_perm"
        )
        test_redirect.__name__ = f"test_image_{image_type}_redirect_rotterdam"
        test_redirect_kappa.__name__ = (
            f"test_image_{image_type}_redirect_kappa"
        )
        test_redirect_australia.__name__ = (
            f"test_image_{image_type}_redirect_australia"
        )
        test_redirect_oct.__name__ = f"test_image_{image_type}_redirect_oct"
        setattr(
            test_class, test_redirect_no_perm.__name__, test_redirect_no_perm
        )
        setattr(test_class, test_redirect.__name__, test_redirect)
        setattr(
            test_class,
            test_redirect_australia.__name__,
            test_redirect_australia,
        )
        setattr(test_class, test_redirect_kappa.__name__, test_redirect_kappa)
        setattr(test_class, test_redirect_oct.__name__, test_redirect_oct)


def create_image_test_method(image_type, reverse_name):
    def test_redirect_no_perm(self, client):
        ds = create_some_datastructure_data()
        url = reverse(
            "retina:api:image-api-view",
            args=[
                image_type,
                ds["patient"].name,
                ds["study"].name,
                ds["image_cf"].name,
                "default",
            ],
        )

        user, _ = get_retina_user_with_token()
        client.force_login(user=user)
        response = client.get(url, follow=True)
        expected_redirect_url = django_reverse(
            reverse_name, args=[ds["image_cf"].id]
        )
        assert status.HTTP_302_FOUND == response.redirect_chain[0][1]
        assert expected_redirect_url == response.redirect_chain[0][0]
        assert status.HTTP_403_FORBIDDEN == response.status_code

    def test_redirect(self, client):
        ds = create_some_datastructure_data()
        url = reverse(
            "retina:api:image-api-view",
            args=[
                image_type,
                ds["patient"].name,
                ds["study"].name,
                ds["image_cf"].name,
                "default",
            ],
        )

        user, _ = get_retina_user_with_token()
        client.force_login(user=user)
        ds["image_cf"].permit_viewing_by_retina_users()

        response = client.get(url, follow=True)
        expected_redirect_url = django_reverse(
            reverse_name, args=[ds["image_cf"].id]
        )
        assert status.HTTP_302_FOUND == response.redirect_chain[0][1]
        assert expected_redirect_url == response.redirect_chain[0][0]
        assert status.HTTP_200_OK == response.status_code

    def test_redirect_australia(self, client):
        ds = create_some_datastructure_data(archive_pars={"name": "Australia"})
        url = reverse(
            "retina:api:image-api-view",
            args=[
                image_type,
                ds["archive"].name,
                ds["patient"].name,
                ds["image_cf"].name,
                "default",
            ],
        )
        user, _ = get_retina_user_with_token()
        client.force_login(user=user)
        ds["image_cf"].permit_viewing_by_retina_users()

        response = client.get(url, follow=True)
        expected_redirect_url = django_reverse(
            reverse_name, args=[ds["image_cf"].id]
        )
        assert response.redirect_chain[0][1] == status.HTTP_302_FOUND
        assert expected_redirect_url == response.redirect_chain[0][0]
        assert status.HTTP_200_OK == response.status_code

    def test_redirect_kappa(self, client):
        ds = create_some_datastructure_data(archive_pars={"name": "kappadata"})
        url = reverse(
            "retina:api:image-api-view",
            args=[
                image_type,
                "Archives",
                ds["archive"].name,
                ds["image_cf"].name,
                "default",
            ],
        )
        user, _ = get_retina_user_with_token()
        client.force_login(user=user)
        ds["image_cf"].permit_viewing_by_retina_users()

        response = client.get(url, follow=True)
        expected_redirect_url = django_reverse(
            reverse_name, args=[ds["image_cf"].id]
        )
        assert response.redirect_chain[0][1] == status.HTTP_302_FOUND
        assert expected_redirect_url == response.redirect_chain[0][0]
        assert status.HTTP_200_OK == response.status_code

    def test_redirect_oct(self, client):
        ds = create_some_datastructure_data()
        url = reverse(
            "retina:api:image-api-view",
            args=[
                image_type,
                ds["patient"].name,
                ds["study_oct"].name,
                ds["image_oct"].name,
                "oct",
            ],
        )
        user, _ = get_retina_user_with_token()
        client.force_login(user=user)
        ds["image_oct"].permit_viewing_by_retina_users()

        response = client.get(url, follow=True)
        expected_redirect_url = django_reverse(
            reverse_name, args=[ds["image_oct"].id]
        )
        assert status.HTTP_302_FOUND == response.redirect_chain[0][1]
        assert expected_redirect_url == response.redirect_chain[0][0]
        assert status.HTTP_200_OK == response.status_code

    return [
        test_redirect_no_perm,
        test_redirect,
        test_redirect_australia,
        test_redirect_kappa,
        test_redirect_oct,
    ]


def batch_test_data_endpoints(test_class):
    for data_type in (
        "Registration",
        "ETDRS",
        "Fovea",
        "Measure",
        "GA",
        "kappa",
    ):
        (
            test_load_no_auth,
            test_load_normal_user_no_auth,
            test_load_no_data,
            test_load_no_data_wrong_user,
            test_load_save_data,
        ) = create_data_test_methods(data_type)

        test_load_no_auth.__name__ = f"test_load_{data_type}_no_auth"
        test_load_normal_user_no_auth.__name__ = "test_load_{}_normal_user_no_auth".format(
            data_type
        )
        test_load_no_data.__name__ = f"test_load_{data_type}_no_data"
        test_load_no_data_wrong_user.__name__ = "test_load_{}_wrong_user".format(
            data_type
        )
        test_load_save_data.__name__ = f"test_load_save_{data_type}"
        setattr(test_class, test_load_no_auth.__name__, test_load_no_auth)
        setattr(
            test_class,
            test_load_normal_user_no_auth.__name__,
            test_load_normal_user_no_auth,
        )
        setattr(test_class, test_load_no_data.__name__, test_load_no_data)
        setattr(
            test_class,
            test_load_no_data_wrong_user.__name__,
            test_load_no_data_wrong_user,
        )
        setattr(test_class, test_load_save_data.__name__, test_load_save_data)


def create_data_test_methods(data_type):  # noqa: C901
    def test_load_no_auth(self, client):
        # create grader user
        user = UserFactory()
        ds = create_some_datastructure_data()
        url = reverse(
            "retina:api:data-api-view",
            args=[data_type, user.id, ds["archive"].name, ds["patient"].name],
        )
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_load_normal_user_no_auth(self, client):
        # create grader user
        user = UserFactory()
        ds = create_some_datastructure_data()
        client, grader = client_login(client, user="normal")
        url = reverse(
            "retina:api:data-api-view",
            args=[data_type, user.id, ds["archive"].name, ds["patient"].name],
        )
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_load_no_data(self, client):
        ds = create_some_datastructure_data()

        # login client
        client, grader = client_login(client, user="retina_user")

        url = reverse(
            "retina:api:data-api-view",
            args=[
                data_type,
                grader.id,
                ds["archive"].name,
                ds["patient"].name,
            ],
        )
        response = client.get(url)
        assert status.HTTP_200_OK == response.status_code
        assert b'{"status":"no data","data":{}}' == response.content

    def test_load_no_data_wrong_user(self, client):
        ds = create_some_datastructure_data()

        # login client
        client, grader = client_login(client, user="retina_user")

        # create grader user
        user = UserFactory()

        url = reverse(
            "retina:api:data-api-view",
            args=[data_type, user.id, ds["archive"].name, ds["patient"].name],
        )
        response = client.get(url)
        assert status.HTTP_403_FORBIDDEN == response.status_code

    def test_load_save_data(self, client):
        # login client
        client, grader = client_login(client, user="retina_user")

        for archive in ("Rotterdam", "Australia", "kappadata"):
            if archive == "Rotterdam" and data_type in ("Measure", "Fovea"):
                continue  # These annotations do not exist for Rotterdam archive type

            if archive == "kappadata" and data_type in (
                "Measure",
                "Fovea",
                "GA",
                "Registration",
            ):
                continue  # These annotations do not exist for kappadata archive type

            ds = create_some_datastructure_data(archive_pars={"name": archive})

            model = create_load_data(data_type, ds, grader)

            url = reverse(
                "retina:api:data-api-view",
                args=[
                    data_type,
                    grader.id,
                    ds["archive"].name,
                    ds["patient"].name,
                ],
            )
            response = client.get(url)

            assert status.HTTP_200_OK == response.status_code
            response_content = json.loads(response.content)
            assert response_content["status"] == "data"
            if isinstance(model, list):
                for single_model in model:
                    response_data_key = single_model.created.strftime(
                        "%Y-%m-%d--%H-%M-%S--%f"
                    )
                    assert response_data_key in response_content["data"]
                    save_request_data = response_content["data"][
                        response_data_key
                    ]

                    response = client.put(
                        url,
                        json.dumps(save_request_data),
                        content_type="application/json",
                    )

                    assert status.HTTP_201_CREATED == response.status_code
                    save_response_content = json.loads(response.content)
                    assert save_response_content["success"]
            else:
                response_data_key = model.created.strftime(
                    "%Y-%m-%d--%H-%M-%S--%f"
                )
                if data_type == "ETDRS" and ds["archive"].name == "Australia":
                    save_request_data = response_content["data"]
                else:
                    assert response_data_key in response_content["data"]
                    save_request_data = response_content["data"][
                        response_data_key
                    ]

                response = client.put(
                    url,
                    json.dumps(save_request_data),
                    content_type="application/json",
                )

                assert status.HTTP_201_CREATED == response.status_code
                response_content = json.loads(response.content)
                assert response_content["success"]

    return (
        test_load_no_auth,
        test_load_normal_user_no_auth,
        test_load_no_data,
        test_load_no_data_wrong_user,
        test_load_save_data,
    )


def create_load_data(data_type, ds, grader):
    if data_type == "Registration":
        model = LandmarkAnnotationSetFactory(grader=grader)
        SingleLandmarkAnnotationFactory(
            annotation_set=model, image=ds["image_cf"]
        ),
        if ds["archive"].name == "Australia":
            # Australia does not allow obs images so create a new cf image for Australia test
            img = ImageFactory(study=ds["study"])
            SingleLandmarkAnnotationFactory(annotation_set=model, image=img)
        else:
            SingleLandmarkAnnotationFactory(
                annotation_set=model, image=ds["image_obs"]
            ),
    elif data_type == "ETDRS":
        model = ETDRSGridAnnotationFactory(grader=grader, image=ds["image_cf"])
    elif data_type == "GA" or data_type == "kappa":
        model_macualar = PolygonAnnotationSetFactory(
            grader=grader, image=ds["image_cf"], name="macular"
        )
        SinglePolygonAnnotationFactory(annotation_set=model_macualar)
        SinglePolygonAnnotationFactory(annotation_set=model_macualar)
        SinglePolygonAnnotationFactory(annotation_set=model_macualar)

        model_peripapillary = PolygonAnnotationSetFactory(
            grader=grader, image=ds["image_cf"], name="peripapillary"
        )
        SinglePolygonAnnotationFactory(annotation_set=model_peripapillary)
        SinglePolygonAnnotationFactory(annotation_set=model_peripapillary)
        SinglePolygonAnnotationFactory(annotation_set=model_peripapillary)
        model = [model_macualar, model_peripapillary]
    elif data_type == "Measure":
        model = [
            MeasurementAnnotationFactory(grader=grader, image=ds["image_cf"]),
            MeasurementAnnotationFactory(grader=grader, image=ds["image_cf"]),
            MeasurementAnnotationFactory(grader=grader, image=ds["image_cf"]),
        ]
    elif data_type == "Fovea":
        model = BooleanClassificationAnnotationFactory(
            grader=grader, image=ds["image_cf"], name="fovea_affected"
        )

    return model
