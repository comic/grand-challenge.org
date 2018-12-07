import json
from rest_framework import status
from django.urls import reverse
from tests.factories import UserFactory
from tests.retina_importers_tests.helpers import get_auth_token_header, get_user_with_token
from tests.retina_images_tests.factories import RetinaImageFactory
from tests.retina_core_tests.factories import create_some_datastructure_data
from tests.registrations_tests.factories import OctObsRegistrationFactory
from tests.annotations_tests.factories import (
    ETDRSGridAnnotationFactory,
    MeasurementAnnotationFactory,
    BooleanClassificationAnnotationFactory,
    PolygonAnnotationSetFactory,
    SinglePolygonAnnotationFactory,
    LandmarkAnnotationSetFactory,
    SingleLandmarkAnnotationFactory,
)


def create_datastructures_data():
    datastructures = create_some_datastructure_data()
    datastructures_aus = create_some_datastructure_data(
        archive_pars={"name": "Australia"}
    )
    oct_obs_registration_aus = OctObsRegistrationFactory(
        oct_series=datastructures_aus["oct_slices"][0],
        obs_image=datastructures_aus["image_obs"],
    )
    oct_obs_registration = OctObsRegistrationFactory(
        oct_series=datastructures["oct_slices"][0],
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
        test_redirect, test_redirect_australia, test_redirect_oct = create_image_test_method(
            image_type, reverse_name
        )
        test_redirect.__name__ = "test_image_{}_redirect_rotterdam".format(
            image_type
        )
        test_redirect_australia.__name__ = "test_image_{}_redirect_australia".format(
            image_type
        )
        test_redirect_oct.__name__ = "test_image_{}_redirect_oct".format(
            image_type
        )
        setattr(test_class, test_redirect.__name__, test_redirect)
        setattr(
            test_class,
            test_redirect_australia.__name__,
            test_redirect_australia,
        )
        setattr(test_class, test_redirect_oct.__name__, test_redirect_oct)


def create_image_test_method(image_type, reverse_name):
    def test_redirect(self, client):
        ds = create_some_datastructure_data()
        url = reverse(
            "retina:image-api-view",
            args=[
                image_type,
                ds["patient"].name,
                ds["study"].name,
                ds["image_cf"].name,
                "default",
            ],
        )

        user, _ = get_user_with_token()
        client.force_login(user=user)
        response = client.get(url, follow=True)
        assert status.HTTP_302_FOUND == response.redirect_chain[0][1]
        assert (
            reverse(reverse_name, args=[ds["image_cf"].id])
            == response.redirect_chain[0][0]
        )
        assert status.HTTP_200_OK == response.status_code

    def test_redirect_australia(self, client):
        ds = create_some_datastructure_data(archive_pars={"name": "Australia"})
        url = reverse(
            "retina:image-api-view",
            args=[
                image_type,
                ds["archive"].name,
                ds["patient"].name,
                ds["image_cf"].name,
                "default",
            ],
        )
        user, _ = get_user_with_token()
        client.force_login(user=user)

        response = client.get(url, follow=True)
        assert response.redirect_chain[0][1] == status.HTTP_302_FOUND
        assert (
            reverse(reverse_name, args=[ds["image_cf"].id])
            == response.redirect_chain[0][0]
        )
        assert status.HTTP_200_OK == response.status_code

    def test_redirect_oct(self, client):
        ds = create_some_datastructure_data()
        url = reverse(
            "retina:image-api-view",
            args=[
                image_type,
                ds["patient"].name,
                ds["study_oct"].name,
                ds["oct_slices"][0].name,
                "oct",
            ],
        )
        user, _ = get_user_with_token()
        client.force_login(user=user)

        response = client.get(url, follow=True)
        assert status.HTTP_302_FOUND == response.redirect_chain[0][1]
        number = len(ds["oct_slices"]) // 2
        oct_image_id = ds["oct_slices"][number].id
        assert (
            reverse(reverse_name, args=[oct_image_id])
            == response.redirect_chain[0][0]
        )
        assert status.HTTP_200_OK == response.status_code

    return [test_redirect, test_redirect_australia, test_redirect_oct]


def batch_test_data_endpoints(test_class):
    for data_type in ("Registration", "ETDRS", "Fovea", "Measure", "GA"):
        test_load_no_auth, test_load_no_data, test_load_save_data = create_data_test_methods(
            data_type
        )

        test_load_no_auth.__name__ = "test_load_{}_no_auth".format(data_type)
        test_load_no_data.__name__ = "test_load_{}_no_data".format(data_type)
        test_load_save_data.__name__ = "test_load_save_{}".format(data_type)
        setattr(test_class, test_load_no_auth.__name__, test_load_no_auth)
        setattr(test_class, test_load_no_data.__name__, test_load_no_data)
        setattr(test_class, test_load_save_data.__name__, test_load_save_data)


def create_data_test_methods(data_type):
    def test_load_no_auth(self, client):
        # create grader user
        username = "grader"
        UserFactory(username=username)
        ds = create_some_datastructure_data()
        url = reverse(
            "retina:data-api-view",
            args=[data_type, username, ds["archive"].name, ds["patient"].name],
        )
        response = client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_load_no_data(self, client):
        ds = create_some_datastructure_data()

        # get token and grader user
        grader, token = get_user_with_token(is_staff=False)
        # get authentication token header
        auth_header = get_auth_token_header("_", token=token)

        url = reverse(
            "retina:data-api-view",
            args=[data_type, grader.username, ds["archive"].name, ds["patient"].name],
        )
        response = client.get(url, **auth_header)
        assert status.HTTP_200_OK == response.status_code
        assert b'{"status":"no data","data":{}}' == response.content

    def test_load_save_data(self, client):
        # get token and grader user
        grader, token = get_user_with_token(is_staff=False)
        # get authentication token header
        auth_header = get_auth_token_header("_", token=token)

        for archive in ("Rotterdam", "Australia"):
            if archive == "Rotterdam" and data_type in ("Measure", "Fovea"):
                continue  # These annotations do not exist for Rotterdam archive type

            ds = create_some_datastructure_data(archive_pars={"name": archive})

            model = create_load_data(data_type, ds, grader)

            url = reverse(
                "retina:data-api-view",
                args=[
                    data_type,
                    grader.username,
                    ds["archive"].name,
                    ds["patient"].name,
                ],
            )
            response = client.get(url, **auth_header)

            assert status.HTTP_200_OK == response.status_code
            response_content = json.loads(response.content)
            assert response_content["status"] == "data"
            if isinstance(model, list):
                for single_model in model:
                    response_data_key = single_model.created.strftime(
                        "%Y-%m-%d--%H-%M-%S--%f"
                    )
                    save_request_data = response_content["data"][
                        response_data_key
                    ]

                    response = client.put(
                        url,
                        json.dumps(save_request_data),
                        content_type="application/json",
                        **auth_header,
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
                    save_request_data = response_content["data"][
                        response_data_key
                    ]

                response = client.put(
                    url,
                    json.dumps(save_request_data),
                    content_type="application/json",
                    **auth_header,
                )

                assert status.HTTP_201_CREATED == response.status_code
                response_content = json.loads(response.content)
                assert response_content["success"]

    return test_load_no_auth, test_load_no_data, test_load_save_data


def create_load_data(data_type, ds, grader):
    if data_type == "Registration":
        model = LandmarkAnnotationSetFactory(grader=grader)
        SingleLandmarkAnnotationFactory(
            annotation_set=model, image=ds["image_cf"]
        ),
        if ds["archive"].name == "Australia":
            # Australia does not allow obs images so create a new cf image for Australia test
            img = RetinaImageFactory(study=ds["study"])
            SingleLandmarkAnnotationFactory(annotation_set=model, image=img)
        else:
            SingleLandmarkAnnotationFactory(
                annotation_set=model, image=ds["image_obs"]
            ),
    elif data_type == "ETDRS":
        model = ETDRSGridAnnotationFactory(grader=grader, image=ds["image_cf"])
    elif data_type == "GA":
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
