import json
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.test import override_settings
from guardian.shortcuts import assign_perm
from requests import put

from grandchallenge.algorithms.models import Job
from grandchallenge.algorithms.serializers import (
    AlgorithmImageSerializer,
    AlgorithmModelSerializer,
)
from grandchallenge.components.models import (
    ComponentInterfaceValue,
    InterfaceKindChoices,
)
from grandchallenge.uploads.models import UserUpload
from tests.algorithms_tests.factories import (
    AlgorithmImageFactory,
    AlgorithmInterfaceFactory,
    AlgorithmJobFactory,
    AlgorithmModelFactory,
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

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_with_multiple_new_inputs(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
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

        value_inputs = [civ.value for civ in job.inputs.all() if civ.value]
        assert "Foo" in value_inputs
        assert True in value_inputs
        assert ["Foo", "bar"] in value_inputs

        image_inputs = [civ.image for civ in job.inputs.all() if civ.image]
        assert algorithm_with_multiple_inputs.image_1 in image_inputs
        assert algorithm_with_multiple_inputs.image_2 in image_inputs
        assert (
            algorithm_with_multiple_inputs.file_upload.filename.split(".")[0]
            in [civ.file for civ in job.inputs.all() if civ.file][0].name
        )

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_with_existing_inputs(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
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

    @override_settings(task_eager_propagates=True, task_always_eager=True)
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

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_with_faulty_file_input(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
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

    @override_settings(task_eager_propagates=True, task_always_eager=True)
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

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_with_faulty_image_input(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
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

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_with_multiple_faulty_existing_image_inputs(
        self,
        client,
        django_capture_on_commit_callbacks,
        algorithm_with_multiple_inputs,
    ):
        ci1, ci2 = ComponentInterfaceFactory.create_batch(
            2, kind=InterfaceKindChoices.MHA_OR_TIFF_SEGMENTATION
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
            "Image segments could not be determined, ensure the voxel values are integers and that it contains no more than 64 segments"
            in str(response.content)
        )
        # and no CIVs should have been created
        assert ComponentInterfaceValue.objects.count() == 0


@pytest.mark.django_db
def test_algorithm_image_download_url(
    client, django_capture_on_commit_callbacks, algorithm_io_image, rf
):
    user1, user2 = UserFactory.create_batch(2)
    group = Group.objects.create(name="test-group")
    group.user_set.add(user1)

    with django_capture_on_commit_callbacks():
        ai = AlgorithmImageFactory(image__from_path=algorithm_io_image)

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
        f"grand-challenge-protected/docker/images/algorithms/algorithmimage/{ai.pk}/algorithm-io-latest.tar"
        in str(resp.url)
    )


@pytest.mark.django_db
def test_algorithm_model_download_url(
    client, django_capture_on_commit_callbacks, algorithm_io_image, rf
):
    user1, user2 = UserFactory.create_batch(2)
    group = Group.objects.create(name="test-group")
    group.user_set.add(user1)

    with django_capture_on_commit_callbacks():
        model = AlgorithmModelFactory(model__from_path=algorithm_io_image)

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
        f"grand-challenge-protected/models/algorithms/algorithmmodel/{model.pk}/algorithm-io-latest.tar"
        in str(resp.url)
    )
