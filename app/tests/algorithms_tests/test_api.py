import json
import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.utils.timezone import now
from guardian.shortcuts import assign_perm
from requests import put
from rest_framework import status

from grandchallenge.algorithms.models import (
    Endpoint,
    EndpointStatusChoices,
    InvocationStatusChoices,
    Job,
)
from grandchallenge.algorithms.serializers import (
    AlgorithmImageSerializer,
    AlgorithmModelSerializer,
)
from grandchallenge.components.models import (
    APIMethodChoices,
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKindChoices,
)
from grandchallenge.uploads.models import UserUpload
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmInterfaceFactory,
    AlgorithmJobFactory,
    AlgorithmModelFactory,
    AlgorithmUserCreditFactory,
    EndpointFactory,
    InvocationFactory,
)
from tests.cases_tests import RESOURCE_PATH
from tests.cases_tests.factories import (
    ImageFileFactoryWithMHDFile,
    RawImageUploadSessionFactory,
)
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, UserFactory
from tests.uploads_tests.factories import (
    UserUploadFactory,
    create_upload_from_file,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_job_detail(client):
    user = UserFactory()
    job = AlgorithmJobFactory(creator=user, time_limit=60)
    response = get_view_for_user(
        viewname="api:algorithms-job-detail",
        client=client,
        user=user,
        reverse_kwargs={"pk": job.pk},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert job.status == job.PENDING
    assert response.json()["status"] == "Queued"


@pytest.mark.django_db
def test_inputs_are_serialized(client):
    u = UserFactory()
    j = AlgorithmJobFactory(creator=u, time_limit=60)

    response = get_view_for_user(client=client, url=j.api_url, user=u)
    assert response.json()["inputs"][0]["image"] == str(
        j.inputs.first().image.api_url.replace("https://", "http://")
    )


@pytest.mark.django_db
def test_durations_are_serialized(client):
    user = UserFactory()
    job = AlgorithmJobFactory(
        creator=user,
        time_limit=60,
        exec_duration=timedelta(seconds=1337),
        invoke_duration=timedelta(seconds=1874),
    )

    response = get_view_for_user(
        client=client, url=job.api_url, user=user
    ).json()

    assert response["exec_duration"] == "P0DT00H22M17S"
    assert response["invoke_duration"] == "P0DT00H31M14S"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "num_jobs",
    (
        1,
        3,
    ),
)
def test_job_list_view_num_queries(
    client, num_jobs, django_assert_max_num_queries
):
    user = UserFactory()
    AlgorithmJobFactory.create_batch(num_jobs, creator=user, time_limit=60)

    with django_assert_max_num_queries(33) as _:
        response = get_view_for_user(
            viewname="api:algorithms-job-list",
            client=client,
            method=client.get,
            user=user,
            content_type="application/json",
        )

        # Sanity checks
        assert response.status_code == 200
        assert len(response.json()["results"]) == num_jobs


@pytest.mark.django_db
class TestJobCreationThroughAPI:

    def create_job(
        self,
        client,
        django_capture_on_commit_callbacks,
        user,
        inputs,
        algorithm,
    ):
        with patch(
            "grandchallenge.components.tasks.execute_job"
        ) as mocked_execute_job:
            # no need to actually execute the job,
            # all other async tasks should run though
            mocked_execute_job.return_value = None
            with django_capture_on_commit_callbacks(execute=True):
                response = get_view_for_user(
                    viewname="api:algorithms-job-list",
                    client=client,
                    method=client.post,
                    user=user,
                    follow=True,
                    content_type="application/json",
                    data={
                        "algorithm": algorithm.api_url,
                        "inputs": inputs,
                    },
                )
        return response

    def create_existing_civs(self, interface_data):
        civ1 = ComponentInterfaceValueFactory(
            interface=interface_data.ci_bool, value=True
        )
        civ2 = ComponentInterfaceValueFactory(
            interface=interface_data.ci_str, value="Foo"
        )
        civ3 = ComponentInterfaceValueFactory(
            interface=interface_data.ci_existing_img,
            image=interface_data.image_2,
        )
        civ4 = ComponentInterfaceValueFactory(
            interface=interface_data.ci_json_in_db_with_schema,
            value=["Foo", "bar"],
        )
        return [civ1, civ2, civ3, civ4]

    def test_create_job_with_multiple_new_inputs(
        self,
        client,
        settings,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
        settings.LAMBDA_TASKS_EAGER = True

        # configure multiple inputs
        interface = AlgorithmInterfaceFactory(
            inputs=[
                algorithm_with_multiple_inputs.ci_json_in_db_with_schema,
                algorithm_with_multiple_inputs.ci_existing_img,
                algorithm_with_multiple_inputs.ci_str,
                algorithm_with_multiple_inputs.ci_bool,
                algorithm_with_multiple_inputs.ci_json_file,
                algorithm_with_multiple_inputs.ci_img_upload,
            ],
            outputs=[ComponentInterfaceFactory()],
        )
        algorithm_with_multiple_inputs.algorithm.interfaces.add(interface)

        assert ComponentInterfaceValue.objects.count() == 0

        response = self.create_job(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_with_multiple_inputs.algorithm,
            user=algorithm_with_multiple_inputs.editor,
            inputs=[
                {
                    "interface": algorithm_with_multiple_inputs.ci_str.slug,
                    "value": "Foo",
                },
                {
                    "interface": algorithm_with_multiple_inputs.ci_bool.slug,
                    "value": True,
                },
                {
                    "interface": algorithm_with_multiple_inputs.ci_img_upload.slug,
                    "upload_session": algorithm_with_multiple_inputs.im_upload_through_api.api_url,
                },
                {
                    "interface": algorithm_with_multiple_inputs.ci_existing_img.slug,
                    "image": algorithm_with_multiple_inputs.image_2.api_url,
                },
                {
                    "interface": algorithm_with_multiple_inputs.ci_json_file.slug,
                    "user_upload": algorithm_with_multiple_inputs.file_upload.api_url,
                },
                {
                    "interface": algorithm_with_multiple_inputs.ci_json_in_db_with_schema.slug,
                    "value": json.loads('["Foo", "bar"]'),
                },
            ],
        )

        assert response.status_code == 201
        assert Job.objects.count() == 1

        job = Job.objects.get()

        assert (
            job.algorithm_image
            == algorithm_with_multiple_inputs.algorithm.active_image
        )
        assert (
            job.algorithm_model
            == algorithm_with_multiple_inputs.algorithm.active_model
        )
        assert job.time_limit == 600
        assert job.inputs.count() == 6

        assert not UserUpload.objects.filter(
            pk=algorithm_with_multiple_inputs.file_upload.pk
        ).exists()

        assert sorted([int.pk for int in interface.inputs.all()]) == sorted(
            [civ.interface.pk for civ in job.inputs.all()]
        )

        value_inputs = [
            civ.value
            for civ in job.inputs.all()
            if civ.interface.super_kind == civ.interface.SuperKind.VALUE
        ]
        assert "Foo" in value_inputs
        assert True in value_inputs
        assert ["Foo", "bar"] in value_inputs

        image_inputs = [
            civ.image
            for civ in job.inputs.all()
            if civ.interface.super_kind == civ.interface.SuperKind.IMAGE
        ]
        assert algorithm_with_multiple_inputs.image_1 in image_inputs
        assert algorithm_with_multiple_inputs.image_2 in image_inputs
        file_inputs = [
            civ.file
            for civ in job.inputs.all()
            if civ.interface.super_kind == civ.interface.SuperKind.FILE
        ]
        assert (
            algorithm_with_multiple_inputs.file_upload.filename.split(".")[0]
            in file_inputs[0].name
        )

    def test_create_job_with_existing_inputs(
        self,
        client,
        settings,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
        settings.LAMBDA_TASKS_EAGER = True

        # configure multiple inputs
        interface = AlgorithmInterfaceFactory(
            inputs=[
                algorithm_with_multiple_inputs.ci_json_in_db_with_schema,
                algorithm_with_multiple_inputs.ci_existing_img,
                algorithm_with_multiple_inputs.ci_str,
                algorithm_with_multiple_inputs.ci_bool,
            ],
            outputs=[ComponentInterfaceFactory()],
        )
        algorithm_with_multiple_inputs.algorithm.interfaces.add(interface)

        civ1, civ2, civ3, civ4 = self.create_existing_civs(
            interface_data=algorithm_with_multiple_inputs
        )
        # TODO test this for existing files, this is not implemented yet
        old_civ_count = ComponentInterfaceValue.objects.count()

        response = self.create_job(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_with_multiple_inputs.algorithm,
            user=algorithm_with_multiple_inputs.editor,
            inputs=[
                {
                    "interface": algorithm_with_multiple_inputs.ci_str.slug,
                    "value": "Foo",
                },
                {
                    "interface": algorithm_with_multiple_inputs.ci_bool.slug,
                    "value": True,
                },
                {
                    "interface": algorithm_with_multiple_inputs.ci_existing_img.slug,
                    "image": algorithm_with_multiple_inputs.image_2.api_url,
                },
                {
                    "interface": algorithm_with_multiple_inputs.ci_json_in_db_with_schema.slug,
                    "value": json.loads('["Foo", "bar"]'),
                },
            ],
        )
        assert response.status_code == 201

        # no new CIVs should have been created
        assert ComponentInterfaceValue.objects.count() == old_civ_count
        # but since there is no job with these inputs yet, a job was created:
        job = Job.objects.get()
        assert job.inputs.count() == 4
        for civ in [civ1, civ2, civ3, civ4]:
            assert civ in job.inputs.all()

    def test_create_job_is_idempotent(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
        # configure multiple inputs
        interface = AlgorithmInterfaceFactory(
            inputs=[
                algorithm_with_multiple_inputs.ci_str,
                algorithm_with_multiple_inputs.ci_bool,
                algorithm_with_multiple_inputs.ci_existing_img,
                algorithm_with_multiple_inputs.ci_json_in_db_with_schema,
            ],
            outputs=[ComponentInterfaceFactory()],
        )
        algorithm_with_multiple_inputs.algorithm.interfaces.add(interface)
        civ1, civ2, civ3, civ4 = self.create_existing_civs(
            interface_data=algorithm_with_multiple_inputs
        )

        job = AlgorithmJobFactory(
            algorithm_image=algorithm_with_multiple_inputs.algorithm.active_image,
            algorithm_model=algorithm_with_multiple_inputs.algorithm.active_model,
            status=Job.SUCCESS,
            time_limit=10,
        )
        job.inputs.set([civ1, civ2, civ3, civ4])
        old_civ_count = ComponentInterfaceValue.objects.count()

        response = self.create_job(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_with_multiple_inputs.algorithm,
            user=algorithm_with_multiple_inputs.editor,
            inputs=[
                {
                    "interface": algorithm_with_multiple_inputs.ci_str.slug,
                    "value": "Foo",
                },
                {
                    "interface": algorithm_with_multiple_inputs.ci_bool.slug,
                    "value": True,
                },
                {
                    "interface": algorithm_with_multiple_inputs.ci_existing_img.slug,
                    "image": algorithm_with_multiple_inputs.image_2.api_url,
                },
                {
                    "interface": algorithm_with_multiple_inputs.ci_json_in_db_with_schema.slug,
                    "value": json.loads('["Foo", "bar"]'),
                },
            ],
        )

        assert response.status_code == 400
        assert (
            "A result for these inputs with the current image and model already exists."
            in str(response.content)
        )
        # no new CIVs should have been created
        assert ComponentInterfaceValue.objects.count() == old_civ_count
        # and no new job because there already is a job with these inputs
        assert Job.objects.count() == 1

    def test_create_job_with_faulty_file_input(
        self,
        client,
        settings,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
        settings.LAMBDA_TASKS_EAGER = True

        # configure file input
        interface = AlgorithmInterfaceFactory(
            inputs=[algorithm_with_multiple_inputs.ci_json_file],
            outputs=[ComponentInterfaceFactory()],
        )
        algorithm_with_multiple_inputs.algorithm.interfaces.add(interface)
        file_upload = UserUploadFactory(
            filename="file.json", creator=algorithm_with_multiple_inputs.editor
        )
        presigned_urls = file_upload.generate_presigned_urls(part_numbers=[1])
        response = put(presigned_urls["1"], data=b'{"Foo": "bar"}')
        file_upload.complete_multipart_upload(
            parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
        )
        file_upload.save()

        response = self.create_job(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_with_multiple_inputs.algorithm,
            user=algorithm_with_multiple_inputs.editor,
            inputs=[
                {
                    "interface": algorithm_with_multiple_inputs.ci_json_file.slug,
                    "user_upload": file_upload.api_url,
                },
            ],
        )

        assert response.status_code == 201
        # validation of files happens async, so job gets created
        assert Job.objects.count() == 1
        job = Job.objects.get()
        # but in cancelled state and with an error message
        assert job.status == Job.CANCELLED
        assert (
            "One or more of the inputs failed validation." == job.error_message
        )
        assert job.detailed_error_message == {
            algorithm_with_multiple_inputs.ci_json_file.title: "JSON does not fulfill schema: instance is not of type 'array'"
        }
        # and no CIVs should have been created
        assert ComponentInterfaceValue.objects.count() == 0

    def test_create_job_with_faulty_json_input(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
        interface = AlgorithmInterfaceFactory(
            inputs=[algorithm_with_multiple_inputs.ci_json_in_db_with_schema],
            outputs=[ComponentInterfaceFactory()],
        )
        algorithm_with_multiple_inputs.algorithm.interfaces.add(interface)

        response = self.create_job(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_with_multiple_inputs.algorithm,
            user=algorithm_with_multiple_inputs.editor,
            inputs=[
                {
                    "interface": algorithm_with_multiple_inputs.ci_json_in_db_with_schema.slug,
                    "value": '{"Foo": "bar"}',
                },
            ],
        )
        # validation of values stored in DB happens synchronously,
        # so no job and no CIVs get created if validation fails
        # error message is reported back to user directly in the form
        assert response.status_code == 400
        assert "JSON does not fulfill schema" in str(response.content)
        assert Job.objects.count() == 0
        assert ComponentInterfaceValue.objects.count() == 0

    def test_create_job_with_faulty_image_input(
        self,
        client,
        settings,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
        settings.LAMBDA_TASKS_EAGER = True

        interface = AlgorithmInterfaceFactory(
            inputs=[algorithm_with_multiple_inputs.ci_img_upload],
            outputs=[ComponentInterfaceFactory()],
        )
        algorithm_with_multiple_inputs.algorithm.interfaces.add(interface)
        user_upload = create_upload_from_file(
            creator=algorithm_with_multiple_inputs.editor,
            file_path=RESOURCE_PATH / "corrupt.png",
        )
        upload_session = RawImageUploadSessionFactory(
            creator=algorithm_with_multiple_inputs.editor
        )
        upload_session.user_uploads.set([user_upload])

        response = self.create_job(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_with_multiple_inputs.algorithm,
            user=algorithm_with_multiple_inputs.editor,
            inputs=[
                {
                    "interface": algorithm_with_multiple_inputs.ci_img_upload.slug,
                    "upload_session": upload_session.api_url,
                },
            ],
        )
        assert response.status_code == 201
        # validation of images happens async, so job gets created
        assert Job.objects.count() == 1
        job = Job.objects.get()
        # but in cancelled state and with an error message
        assert job.status == Job.CANCELLED
        assert (
            "One or more of the inputs failed validation." == job.error_message
        )
        assert "1 file could not be imported" in str(
            job.detailed_error_message
        )
        # and no CIVs should have been created
        assert ComponentInterfaceValue.objects.count() == 0

    def test_create_job_with_multiple_faulty_existing_image_inputs(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
        ci1, ci2 = ComponentInterfaceFactory.create_batch(
            2, kind=InterfaceKindChoices.PANIMG_SEGMENTATION
        )

        for ci in [ci1, ci2]:
            ci.overlay_segments = [
                {"name": "s1", "visible": True, "voxel_value": 1}
            ]
            ci.save()

        interface = AlgorithmInterfaceFactory(
            inputs=[ci1, ci2], outputs=[ComponentInterfaceFactory()]
        )
        algorithm_with_multiple_inputs.algorithm.interfaces.add(interface)

        im = ImageFactory()
        im.files.set([ImageFileFactoryWithMHDFile()])
        assign_perm(
            "cases.view_image", algorithm_with_multiple_inputs.editor, im
        )

        response = self.create_job(
            client=client,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
            algorithm=algorithm_with_multiple_inputs.algorithm,
            user=algorithm_with_multiple_inputs.editor,
            inputs=[
                {
                    "interface": ci1.slug,
                    "image": im.api_url,
                },
                {
                    "interface": ci2.slug,
                    "image": im.api_url,
                },
            ],
        )

        assert response.status_code == 400
        # no job is created, because validation of existing images happens on the serializer
        assert Job.objects.count() == 0
        assert (
            "Image segments could not be determined, ensure the voxel values are integers and that it contains no more than 2 segments"
            in str(response.content)
        )
        # and no CIVs should have been created
        assert ComponentInterfaceValue.objects.count() == 0


@pytest.mark.django_db
def test_algorithm_image_download_url(client, rf):
    user1, user2 = UserFactory.create_batch(2)
    group = Group.objects.create(name="test-group")
    group.user_set.add(user1)

    ai = AlgorithmImageFactory()

    assign_perm("algorithms.download_algorithmimage", group, ai)

    serialized_ai = AlgorithmImageSerializer(
        ai, context={"request": rf.get("/foo", secure=True)}
    ).data

    resp = get_view_for_user(
        url=serialized_ai["image"], client=client, user=user2
    )
    assert resp.status_code == 403

    resp = get_view_for_user(
        url=serialized_ai["image"], client=client, user=user1
    )
    assert resp.status_code == 302
    assert (
        f"grand-challenge-protected/docker/images/algorithms/algorithmimage/{ai.pk}/example.dat"
        in str(resp.url)
    )


@pytest.mark.django_db
def test_algorithm_model_download_url(client, rf):
    user1, user2 = UserFactory.create_batch(2)
    group = Group.objects.create(name="test-group")
    group.user_set.add(user1)

    model = AlgorithmModelFactory()

    assign_perm("algorithms.download_algorithmmodel", group, model)

    serialized_model = AlgorithmModelSerializer(
        model, context={"request": rf.get("/foo", secure=True)}
    ).data

    resp = get_view_for_user(
        url=serialized_model["model"], client=client, user=user2
    )
    assert resp.status_code == 403

    resp = get_view_for_user(
        url=serialized_model["model"], client=client, user=user1
    )
    assert resp.status_code == 302
    assert (
        f"grand-challenge-protected/models/algorithms/algorithmmodel/{model.pk}/example.dat"
        in str(resp.url)
    )


@pytest.mark.django_db
class TestEndpointList:
    url = "/api/v1/algorithms/endpoints/"

    def test_anonymous_returns_empty_list(self, client):
        EndpointFactory()
        response = client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_authenticated_user_sees_nothing_without_permissions(self, client):
        EndpointFactory()
        user = UserFactory()
        client.force_login(user=user)
        response = client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_creator_can_list_own_endpoint(self, client):
        endpoint = EndpointFactory()
        client.force_login(user=endpoint.creator)
        response = client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["pk"] == str(endpoint.pk)

    def test_viewer_group_member_can_list_endpoint(self, client):
        endpoint = EndpointFactory()
        user = UserFactory()
        endpoint.viewers_group.user_set.add(user)
        client.force_login(user=user)
        response = client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    def test_user_only_sees_permitted_endpoints(self, client):
        user = UserFactory()
        visible = EndpointFactory()
        EndpointFactory()  # not visible
        visible.viewers_group.user_set.add(user)
        client.force_login(user=user)
        response = client.get(self.url)
        assert response.data["count"] == 1
        assert response.data["results"][0]["pk"] == str(visible.pk)

    def test_filter_by_algorithm(self, client):
        e1 = EndpointFactory()
        EndpointFactory(creator=e1.creator)
        client.force_login(user=e1.creator)
        algorithm = e1.algorithm_image.algorithm
        response = client.get(self.url, {"algorithm": str(algorithm.pk)})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0][
            "algorithm"
        ] == algorithm.api_url.replace("https://", "http://")

    def test_filter_by_status(self, client):
        endpoint = EndpointFactory(status=Endpoint.StatusChoices.RUNNING)
        EndpointFactory(
            status=Endpoint.StatusChoices.QUEUED, creator=endpoint.creator
        )
        client.force_login(user=endpoint.creator)
        response = client.get(self.url, {"status": "Running"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["pk"] == str(endpoint.pk)

    def test_filter_by_status_invalid(self, client):
        endpoint = EndpointFactory()
        client.force_login(user=endpoint.creator)
        response = client.get(self.url, {"status": "nonsense"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0


@pytest.mark.django_db
class TestEndpointDetail:
    def get_url(self, pk):
        return f"/api/v1/algorithms/endpoints/{pk}/"

    def test_anonymous_returns_empty_for_existing(self, client):
        endpoint = EndpointFactory()
        response = client.get(self.get_url(endpoint.pk))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_no_permission_returns_404(self, client):
        user = UserFactory()
        endpoint = EndpointFactory()
        client.force_login(user=user)
        response = client.get(self.get_url(endpoint.pk))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_creator_can_retrieve(self, client):
        endpoint = EndpointFactory()
        client.force_login(user=endpoint.creator)
        response = client.get(self.get_url(endpoint.pk))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["pk"] == str(endpoint.pk)

    def test_viewer_group_member_can_retrieve(self, client):
        user = UserFactory()
        endpoint = EndpointFactory()
        endpoint.viewers_group.user_set.add(user)
        client.force_login(user=user)
        response = client.get(self.get_url(endpoint.pk))
        assert response.status_code == status.HTTP_200_OK

    def test_nonexistent_returns_404(self, client):
        user = UserFactory()
        client.force_login(user=user)
        response = client.get(self.get_url(uuid.uuid4()))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_remaining_lifetime(self, client):
        endpoint = EndpointFactory.create()
        client.force_login(user=endpoint.creator)

        response = client.get(self.get_url(endpoint.pk))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["remaining_lifetime"].startswith("P0DT00H09M")

        endpoint.status = EndpointStatusChoices.STOPPED
        endpoint.save()

        response = client.get(self.get_url(endpoint.pk))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["remaining_lifetime"] == "P0DT00H00M00S"


@pytest.mark.django_db
class TestEndpointCreate:
    url = "/api/v1/algorithms/endpoints/"

    def test_anonymous_returns_not_authenticated(self, client):
        response = client.post(self.url, data={})
        assert (
            response.status_code == status.HTTP_401_UNAUTHORIZED
        ), response.data

    def test_no_permission_returns_403(self, client):
        user = UserFactory()
        algorithm = AlgorithmFactory()

        client.force_login(user=user)
        response = client.post(self.url, data={"algorithm": algorithm.api_url})

        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data

    def test_user_without_algorithm_access_cannot_create_endpoint(
        self, client
    ):
        user = UserFactory()
        assign_perm("algorithms.add_endpoint", user)
        algorithm = AlgorithmFactory()

        client.force_login(user=user)
        response = client.post(self.url, data={"algorithm": algorithm.api_url})

        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), response.data
        assert response.data["algorithm"][0].code == "does_not_exist"

    def test_cannot_create_endpoint_without_credits(self, client):
        user = UserFactory()
        assign_perm("algorithms.add_endpoint", user)
        algorithm = AlgorithmFactory()
        algorithm.add_editor(user)
        AlgorithmImageFactory(
            algorithm=algorithm,
            api_method=APIMethodChoices.INVOKE,
            is_desired_version=True,
            is_manifest_valid=True,
            is_in_registry=True,
        )

        client.force_login(user=user)
        response = client.post(self.url, data={"algorithm": algorithm.api_url})

        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), response.data
        assert (
            str(response.data["non_field_errors"][0])
            == "You have run out of algorithm credits"
        )

    def test_user_with_permission_can_create_endpoint(self, client):
        user = UserFactory()
        assign_perm("algorithms.add_endpoint", user)
        algorithm = AlgorithmFactory()
        algorithm.add_user(user)
        AlgorithmImageFactory(
            algorithm=algorithm,
            api_method=APIMethodChoices.INVOKE,
            is_desired_version=True,
            is_manifest_valid=True,
            is_in_registry=True,
        )
        AlgorithmUserCreditFactory(
            algorithm=algorithm,
            user=user,
            credits=1000,
            valid_from=now().date(),
            valid_until=now().date(),
            comment="test",
        )

        client.force_login(user=user)
        response = client.post(self.url, data={"algorithm": algorithm.api_url})

        assert response.status_code == status.HTTP_201_CREATED, response.data

    def test_editor_with_permission_can_create_endpoint(self, client):
        user = UserFactory()
        assign_perm("algorithms.add_endpoint", user)
        algorithm = AlgorithmFactory()
        algorithm.add_editor(user)
        AlgorithmImageFactory(
            algorithm=algorithm,
            api_method=APIMethodChoices.INVOKE,
            is_desired_version=True,
            is_manifest_valid=True,
            is_in_registry=True,
        )
        AlgorithmUserCreditFactory(
            algorithm=algorithm,
            user=user,
            credits=1000,
            valid_from=now().date(),
            valid_until=now().date(),
            comment="test",
        )

        client.force_login(user=user)
        response = client.post(self.url, data={"algorithm": algorithm.api_url})

        assert response.status_code == status.HTTP_201_CREATED, response.data

    def test_cannot_create_endpoint_with_exec_image(self, client):
        user = UserFactory()
        assign_perm("algorithms.add_endpoint", user)
        algorithm = AlgorithmFactory()
        algorithm.add_editor(user)
        AlgorithmImageFactory(
            algorithm=algorithm,
            api_method=APIMethodChoices.EXEC,
            is_desired_version=True,
            is_manifest_valid=True,
            is_in_registry=True,
        )

        client.force_login(user=user)
        response = client.post(self.url, data={"algorithm": algorithm.api_url})

        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), response.data
        assert (
            str(response.data["non_field_errors"][0])
            == "Algorithm image does not implement the invoke API"
        )

    def test_cannot_create_endpoint_without_active_image(self, client):
        user = UserFactory()
        assign_perm("algorithms.add_endpoint", user)
        algorithm = AlgorithmFactory()
        algorithm.add_editor(user)

        client.force_login(user=user)
        response = client.post(self.url, data={"algorithm": algorithm.api_url})

        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), response.data
        assert (
            str(response.data["non_field_errors"][0])
            == "Algorithm image is not ready to be used"
        )

    def test_cannot_create_multiple_endpoints_for_algorithm(self, client):
        user = UserFactory()
        assign_perm("algorithms.add_endpoint", user)
        algorithm = AlgorithmFactory()
        algorithm.add_editor(user)
        algorithm_image = AlgorithmImageFactory(
            algorithm=algorithm,
            api_method=APIMethodChoices.INVOKE,
            is_desired_version=True,
            is_manifest_valid=True,
            is_in_registry=True,
        )
        AlgorithmUserCreditFactory(
            algorithm=algorithm,
            user=user,
            credits=1000,
            valid_from=now().date(),
            valid_until=now().date(),
            comment="test",
        )
        EndpointFactory(creator=user, algorithm_image=algorithm_image)

        client.force_login(user=user)
        response = client.post(self.url, data={"algorithm": algorithm.api_url})

        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), response.data
        assert (
            str(response.data["non_field_errors"][0])
            == "You already have an active endpoint for this algorithm"
        )

    def test_can_create_endpoint_with_existing_from_other_user(self, client):
        user = UserFactory()
        assign_perm("algorithms.add_endpoint", user)
        algorithm = AlgorithmFactory()
        algorithm.add_editor(user)
        algorithm_image = AlgorithmImageFactory(
            algorithm=algorithm,
            api_method=APIMethodChoices.INVOKE,
            is_desired_version=True,
            is_manifest_valid=True,
            is_in_registry=True,
        )
        AlgorithmUserCreditFactory(
            algorithm=algorithm,
            user=user,
            credits=1000,
            valid_from=now().date(),
            valid_until=now().date(),
            comment="test",
        )
        EndpointFactory(algorithm_image=algorithm_image)

        client.force_login(user=user)
        response = client.post(self.url, data={"algorithm": algorithm.api_url})

        assert response.status_code == status.HTTP_201_CREATED, response.data

    def test_cannot_create_too_many_active_endpoints(self, client, settings):
        settings.ALGORITHM_ENDPOINTS_MAX_ACTIVE_ENDPOINTS_PER_USER = 1
        user = UserFactory()
        assign_perm("algorithms.add_endpoint", user)
        algorithm = AlgorithmFactory()
        algorithm.add_editor(user)
        AlgorithmImageFactory(
            algorithm=algorithm,
            api_method=APIMethodChoices.INVOKE,
            is_desired_version=True,
            is_manifest_valid=True,
            is_in_registry=True,
        )
        AlgorithmUserCreditFactory(
            algorithm=algorithm,
            user=user,
            credits=1000,
            valid_from=now().date(),
            valid_until=now().date(),
            comment="test",
        )
        endpoint = EndpointFactory(creator=user)

        client.force_login(user=user)
        response = client.post(self.url, data={"algorithm": algorithm.api_url})

        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), response.data
        assert (
            str(response.data["non_field_errors"][0])
            == "You have too many active endpoints"
        )

        endpoint.status = EndpointStatusChoices.STOPPED
        endpoint.save()

        client.force_login(user=user)
        response = client.post(self.url, data={"algorithm": algorithm.api_url})

        assert response.status_code == status.HTTP_201_CREATED, response.data


@pytest.mark.django_db
class TestEndpointCreateReadUpdateOnly:
    url = "/api/v1/algorithms/endpoints/"

    def test_delete_not_allowed(self, client):
        endpoint = EndpointFactory()
        client.force_login(user=endpoint.creator)
        response = client.delete(f"{self.url}{endpoint.pk}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestEndpointKeepAlive:
    def get_url(self, pk):
        return f"/api/v1/algorithms/endpoints/{pk}/keep_alive/"

    def test_anonymous_returns_401(self, client):
        endpoint = EndpointFactory.create()
        response = client.patch(self.get_url(endpoint.pk))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_no_permission_returns_404(self, client):
        user = UserFactory()
        endpoint = EndpointFactory()
        client.force_login(user=user)
        response = client.patch(self.get_url(endpoint.pk))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_viewer_group_member_cannot_extend_lifetime(self, client):
        user = UserFactory()
        endpoint = EndpointFactory.create(
            maximum_duration=timedelta(seconds=1)
        )
        endpoint.viewers_group.user_set.add(user)
        AlgorithmUserCreditFactory(
            user=user,
            algorithm=endpoint.algorithm_image.algorithm,
            credits=1000,
            valid_from=now().date(),
            valid_until=now().date(),
            comment="test",
        )
        client.force_login(user=user)

        response = client.patch(self.get_url(endpoint.pk))

        assert response.status_code == 403, response.data
        endpoint.refresh_from_db()
        assert endpoint.maximum_duration == timedelta(seconds=1)

    def test_duration_limit_reached(self, client):
        endpoint = EndpointFactory.create()
        client.force_login(user=endpoint.creator)
        client.raise_request_exception = True

        response = client.patch(self.get_url(endpoint.pk))

        assert response.status_code == 400, response.data
        assert response.json() == {"status": "Endpoint duration limit reached"}
        endpoint.refresh_from_db()
        assert endpoint.maximum_duration < timedelta(seconds=300)

    def test_maximum_duration_extended(self, client):
        endpoint = EndpointFactory.create(
            maximum_duration=timedelta(seconds=1)
        )
        AlgorithmUserCreditFactory(
            user=endpoint.creator,
            algorithm=endpoint.algorithm_image.algorithm,
            credits=1000,
            valid_from=now().date(),
            valid_until=now().date(),
            comment="test",
        )
        client.force_login(user=endpoint.creator)
        client.raise_request_exception = True

        response = client.patch(self.get_url(endpoint.pk))

        assert response.status_code == 200, response.data
        assert response.json() == {"status": "Endpoint lifetime extended"}
        endpoint.refresh_from_db()
        assert (
            endpoint.maximum_duration
            == endpoint.endpoint_utilization.duration + timedelta(seconds=300)
        )


@pytest.mark.django_db
class TestInvocationList:
    url = "/api/v1/algorithms/invocations/"

    def test_anonymous_returns_empty_list(self, client):
        InvocationFactory()

        response = client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_authenticated_user_sees_nothing_without_permissions(self, client):
        InvocationFactory()
        user = UserFactory()

        client.force_login(user=user)
        response = client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_endpoint_creator_can_list_invocation(self, client):
        invocation = InvocationFactory()

        client.force_login(user=invocation.endpoint.creator)
        response = client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["pk"] == str(invocation.pk)

    def test_endpoint_viewer_group_member_can_list_invocation(self, client):
        invocation = InvocationFactory()
        user = UserFactory()
        invocation.endpoint.viewers_group.user_set.add(user)

        client.force_login(user=user)
        response = client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["pk"] == str(invocation.pk)

    def test_user_only_sees_invocations_from_permitted_endpoints(self, client):
        user = UserFactory()
        visible = InvocationFactory()
        InvocationFactory()  # not visible
        visible.endpoint.viewers_group.user_set.add(user)

        client.force_login(user=user)
        response = client.get(self.url)

        assert response.data["count"] == 1
        assert response.data["results"][0]["pk"] == str(visible.pk)

    def test_filter_by_status(self, client):
        invocation = InvocationFactory(
            status=InvocationStatusChoices.EXECUTING
        )
        InvocationFactory(
            endpoint=invocation.endpoint,
            status=InvocationStatusChoices.QUEUED,
        )

        client.force_login(user=invocation.endpoint.creator)
        response = client.get(self.url, {"status": "Executing"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["pk"] == str(invocation.pk)

    def test_filter_by_status_invalid(self, client):
        invocation = InvocationFactory()

        client.force_login(user=invocation.endpoint.creator)
        response = client.get(self.url, {"status": "nonsense"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0


@pytest.mark.django_db
class TestInvocationDetail:
    url = "/api/v1/algorithms/invocations/"

    def get_url(self, pk):
        return f"{self.url}{pk}/"

    def test_anonymous_returns_empty_for_existing(self, client):
        invocation = InvocationFactory()

        response = client.get(self.get_url(invocation.pk))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_no_permission_returns_404(self, client):
        user = UserFactory()
        invocation = InvocationFactory()

        client.force_login(user=user)
        response = client.get(self.get_url(invocation.pk))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_endpoint_creator_can_retrieve(self, client):
        invocation = InvocationFactory()

        client.force_login(user=invocation.endpoint.creator)
        response = client.get(self.get_url(invocation.pk))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["pk"] == str(invocation.pk)

    def test_endpoint_viewer_group_member_can_retrieve(self, client):
        user = UserFactory()
        invocation = InvocationFactory()
        invocation.endpoint.viewers_group.user_set.add(user)

        client.force_login(user=user)
        response = client.get(self.get_url(invocation.pk))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["pk"] == str(invocation.pk)

    def test_nonexistent_returns_404(self, client):
        user = UserFactory()

        client.force_login(user=user)
        response = client.get(self.get_url(uuid.uuid4()))

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestInvocationCreate:
    url = "/api/v1/algorithms/invocations/"

    def test_anonymous_returns_not_authenticated(self, client):
        response = client.post(self.url, data={})
        assert (
            response.status_code == status.HTTP_401_UNAUTHORIZED
        ), response.data

    def test_no_permission_returns_400(self, client):
        user = UserFactory()
        endpoint = EndpointFactory(
            status=EndpointStatusChoices.RUNNING,
        )

        client.force_login(user=user)
        response = client.post(self.url, data={"endpoint": endpoint.api_url})

        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), response.data
        assert response.data["endpoint"][0].code == "does_not_exist"

    def test_endpoint_creator_can_create_invocation(self, client):
        user = UserFactory()
        endpoint = EndpointFactory(
            creator=user,
            status=EndpointStatusChoices.RUNNING,
        )
        ci_string = ComponentInterfaceFactory(
            kind=ComponentInterface.Kind.STRING
        )
        interface = AlgorithmInterfaceFactory(inputs=[ci_string])
        endpoint.algorithm_image.algorithm.interfaces.add(interface)

        client.force_login(user=user)
        response = client.post(
            self.url,
            content_type="application/json",
            data={
                "endpoint": endpoint.api_url,
                "inputs": [
                    {"interface": ci_string.slug, "value": "foo"},
                ],
            },
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data

    def test_can_only_create_invocation_for_permitted_endpoints(self, client):
        user = UserFactory()
        EndpointFactory(
            creator=user,
            status=EndpointStatusChoices.RUNNING,
        )
        endpoint = EndpointFactory(status=EndpointStatusChoices.RUNNING)
        ci_string = ComponentInterfaceFactory(
            kind=ComponentInterface.Kind.STRING
        )
        interface = AlgorithmInterfaceFactory(inputs=[ci_string])
        endpoint.algorithm_image.algorithm.interfaces.add(interface)

        client.force_login(user=user)
        response = client.post(
            self.url,
            content_type="application/json",
            data={
                "endpoint": endpoint.api_url,
                "inputs": [
                    {"interface": ci_string.slug, "value": "foo"},
                ],
            },
        )

        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), response.data
        assert response.data["endpoint"][0].code == "does_not_exist"

    def test_can_only_create_invocation_for_running_endpoints(self, client):
        user = UserFactory()
        endpoint = EndpointFactory(
            creator=user,
            status=EndpointStatusChoices.QUEUED,
        )
        ci_string = ComponentInterfaceFactory(
            kind=ComponentInterface.Kind.STRING
        )
        interface = AlgorithmInterfaceFactory(inputs=[ci_string])
        endpoint.algorithm_image.algorithm.interfaces.add(interface)

        client.force_login(user=user)
        response = client.post(
            self.url,
            content_type="application/json",
            data={
                "endpoint": endpoint.api_url,
                "inputs": [
                    {"interface": ci_string.slug, "value": "foo"},
                ],
            },
        )

        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), response.data
        assert response.data["endpoint"][0].code == "does_not_exist"

    def test_endpoint_viewer_group_member_cannot_create_invocation(
        self, client
    ):
        user = UserFactory()
        endpoint = EndpointFactory(status=EndpointStatusChoices.RUNNING)
        endpoint.viewers_group.user_set.add(user)

        client.force_login(user=user)
        response = client.post(self.url, data={"endpoint": endpoint.api_url})

        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), response.data
        assert response.data["endpoint"][0].code == "does_not_exist"

    def test_endpoint_limit_active_invocations(self, client, settings):
        user = UserFactory()
        endpoint = EndpointFactory(
            creator=user,
            status=EndpointStatusChoices.RUNNING,
        )
        ci_string = ComponentInterfaceFactory(
            kind=ComponentInterface.Kind.STRING
        )
        interface = AlgorithmInterfaceFactory(inputs=[ci_string])
        endpoint.algorithm_image.algorithm.interfaces.add(interface)
        InvocationFactory.create_batch(
            settings.ALGORITHM_ENDPOINTS_MAX_ACTIVE_INVOCATIONS_PER_ENDPOINT,
            endpoint=endpoint,
        )

        client.force_login(user=user)
        response = client.post(
            self.url,
            content_type="application/json",
            data={
                "endpoint": endpoint.api_url,
                "inputs": [
                    {"interface": ci_string.slug, "value": "foo"},
                ],
            },
        )

        assert (
            response.status_code == status.HTTP_400_BAD_REQUEST
        ), response.data
        assert response.json() == {
            "non_field_errors": [
                "There are too many active invocations for this endpoint, "
                "please try again after they have completed"
            ]
        }


@pytest.mark.django_db
class TestInvocationReadCreateOnly:
    url = "/api/v1/algorithms/invocations/"

    def get_url(self, pk):
        return f"{self.url}{pk}/"

    def test_put_not_allowed(self, client):
        invocation = InvocationFactory()
        client.force_login(user=invocation.endpoint.creator)
        response = client.put(self.get_url(invocation.pk), data={})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_patch_not_allowed(self, client):
        invocation = InvocationFactory()
        client.force_login(user=invocation.endpoint.creator)
        response = client.patch(self.get_url(invocation.pk), data={})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_not_allowed(self, client):
        invocation = InvocationFactory()
        client.force_login(user=invocation.endpoint.creator)
        response = client.delete(self.get_url(invocation.pk))
        assert response.status_code == status.HTTP_403_FORBIDDEN
