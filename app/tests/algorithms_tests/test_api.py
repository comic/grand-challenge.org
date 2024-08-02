import json
from unittest.mock import patch

import pytest
from django.test import TestCase, override_settings
from guardian.shortcuts import assign_perm
from requests import put

from grandchallenge.algorithms.models import Job
from grandchallenge.components.models import (
    ComponentInterfaceValue,
    InterfaceKind,
)
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
    AlgorithmModelFactory,
)
from tests.cases_tests.factories import (
    ImageFactoryWithImageFile,
    RawImageUploadSessionFactory,
)
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import UserFactory
from tests.uploads_tests.factories import UserUploadFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_job_detail(client):
    user = UserFactory()
    job = AlgorithmJobFactory(creator=user)
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
    j = AlgorithmJobFactory(creator=u)

    response = get_view_for_user(client=client, url=j.api_url, user=u)
    assert response.json()["inputs"][0]["image"] == str(
        j.inputs.first().image.api_url.replace("https://", "http://")
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "num_jobs",
    (
        (1),
        (3),
    ),
)
def test_job_list_view_num_queries(
    client, django_assert_num_queries, num_jobs
):
    user = UserFactory()
    AlgorithmJobFactory.create_batch(num_jobs, creator=user)

    with django_assert_num_queries(33) as _:
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


class TestJobCreation(TestCase):

    def setUp(self):
        self.algorithm = AlgorithmFactory(time_limit=600)
        self.algorithm_image = AlgorithmImageFactory(
            algorithm=self.algorithm,
            is_desired_version=True,
            is_manifest_valid=True,
            is_in_registry=True,
        )
        self.algorithm_model = AlgorithmModelFactory(
            algorithm=self.algorithm,
            is_desired_version=True,
        )

        self.user = UserFactory()
        self.algorithm.add_editor(user=self.user)

        # create 1 interface of each kind
        self.ci_str = ComponentInterfaceFactory(
            kind=InterfaceKind.InterfaceKindChoices.STRING
        )
        self.ci_bool = ComponentInterfaceFactory(
            kind=InterfaceKind.InterfaceKindChoices.BOOL
        )
        self.ci_img_upload = ComponentInterfaceFactory(
            kind=InterfaceKind.InterfaceKindChoices.IMAGE
        )
        self.ci_existing_img = ComponentInterfaceFactory(
            kind=InterfaceKind.InterfaceKindChoices.IMAGE
        )
        self.ci_json_in_db_with_schema = ComponentInterfaceFactory(
            kind=InterfaceKind.InterfaceKindChoices.ANY,
            store_in_database=True,
            schema={
                "$schema": "http://json-schema.org/draft-07/schema",
                "type": "array",
            },
        )
        self.ci_json_file = ComponentInterfaceFactory(
            kind=InterfaceKind.InterfaceKindChoices.ANY,
            store_in_database=False,
            schema={
                "$schema": "http://json-schema.org/draft-07/schema",
                "type": "array",
            },
        )

        self.algorithm.inputs.set(
            [
                self.ci_str,
                self.ci_bool,
                self.ci_json_file,
                self.ci_json_in_db_with_schema,
                self.ci_existing_img,
                self.ci_img_upload,
            ]
        )

        # Create inputs
        self.im_upload = RawImageUploadSessionFactory(creator=self.user)
        self.image_1 = ImageFactoryWithImageFile()
        self.image_2 = ImageFactoryWithImageFile()
        # couldn't figure out a way to just attach one file, so using the factory
        # and deleting the second file
        for im in [self.image_1, self.image_2]:
            im.files.set([self.image_2.files.all()[0]])
            assign_perm("cases.view_image", self.user, im)
        self.im_upload.image_set.set([self.image_1])
        self.file_upload = UserUploadFactory(
            filename="file.json", creator=self.user
        )
        presigned_urls = self.file_upload.generate_presigned_urls(
            part_numbers=[1]
        )
        response = put(presigned_urls["1"], data=b'["Foo", "bar"]')
        self.file_upload.complete_multipart_upload(
            parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
        )
        self.file_upload.save()

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_with_new_inputs(self):
        assert ComponentInterfaceValue.objects.count() == 0

        with patch(
            "grandchallenge.components.tasks.execute_job"
        ) as mocked_execute_job:
            # no need to actually execute the job,
            # all other async tasks should run though
            mocked_execute_job.return_value = None
            with self.captureOnCommitCallbacks(execute=True):
                response = get_view_for_user(
                    viewname="api:algorithms-job-list",
                    client=self.client,
                    method=self.client.post,
                    user=self.user,
                    follow=True,
                    content_type="application/json",
                    data={
                        "algorithm": self.algorithm.api_url,
                        "inputs": [
                            {"interface": self.ci_str.slug, "value": "Foo"},
                            {"interface": self.ci_bool.slug, "value": True},
                            {
                                "interface": self.ci_img_upload.slug,
                                "upload_session": self.im_upload.api_url,
                            },
                            {
                                "interface": self.ci_existing_img.slug,
                                "image": self.image_2.api_url,
                            },
                            {
                                "interface": self.ci_json_file.slug,
                                "user_upload": self.file_upload.api_url,
                            },
                            {
                                "interface": self.ci_json_in_db_with_schema.slug,
                                "value": json.loads('["Foo", "bar"]'),
                            },
                        ],
                    },
                )

        assert response.status_code == 201

        job = Job.objects.get()

        assert job.algorithm_image == self.algorithm_image
        assert job.algorithm_model == self.algorithm_model
        assert job.time_limit == 600
        assert job.inputs.count() == 6

        assert sorted(
            [int.pk for int in self.algorithm.inputs.all()]
        ) == sorted([civ.interface.pk for civ in job.inputs.all()])

        value_inputs = [civ.value for civ in job.inputs.all() if civ.value]
        assert "Foo" in value_inputs
        assert True in value_inputs
        assert json.loads('["Foo", "bar"]') in value_inputs

        image_inputs = [civ.image for civ in job.inputs.all() if civ.image]
        assert self.image_1 in image_inputs
        assert self.image_2 in image_inputs

        assert (
            self.file_upload.filename
            in [civ.file for civ in job.inputs.all() if civ.file][0].name
        )

    @override_settings(task_eager_propagates=True, task_always_eager=True)
    def test_create_job_with_existing_inputs(self):
        civ1 = ComponentInterfaceValueFactory(
            interface=self.ci_bool, value=True
        )
        civ2 = ComponentInterfaceValueFactory(
            interface=self.ci_str, value="Foo"
        )
        civ3 = ComponentInterfaceValueFactory(
            interface=self.ci_existing_img, image=self.image_2
        )
        civ4 = ComponentInterfaceValueFactory(
            interface=self.ci_json_in_db_with_schema,
            value=json.loads('["Foo", "bar"]'),
        )
        # TODO test this for existing files, this is not implemented in gcapi yet

        old_civ_count = ComponentInterfaceValue.objects.count()

        # remove upload interfaces from algorithm
        self.algorithm.inputs.remove(self.ci_img_upload, self.ci_json_file)

        with patch(
            "grandchallenge.components.tasks.execute_job"
        ) as mocked_execute_job:
            # no need to actually execute the job,
            # all other async tasks should run though
            mocked_execute_job.return_value = None
            with self.captureOnCommitCallbacks(execute=True):
                response = get_view_for_user(
                    viewname="api:algorithms-job-list",
                    client=self.client,
                    method=self.client.post,
                    user=self.user,
                    follow=True,
                    content_type="application/json",
                    data={
                        "algorithm": self.algorithm.api_url,
                        "inputs": [
                            {"interface": self.ci_str.slug, "value": "Foo"},
                            {"interface": self.ci_bool.slug, "value": True},
                            {
                                "interface": self.ci_existing_img.slug,
                                "image": self.image_2.api_url,
                            },
                            {
                                "interface": self.ci_json_in_db_with_schema.slug,
                                "value": json.loads('["Foo", "bar"]'),
                            },
                        ],
                    },
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
    def test_create_job_with_existing_inputs_idempotency(self):
        civ1 = ComponentInterfaceValueFactory(
            interface=self.ci_bool, value=True
        )
        civ2 = ComponentInterfaceValueFactory(
            interface=self.ci_str, value="Foo"
        )
        civ3 = ComponentInterfaceValueFactory(
            interface=self.ci_existing_img, image=self.image_2
        )
        civ4 = ComponentInterfaceValueFactory(
            interface=self.ci_json_in_db_with_schema,
            value=json.loads('["Foo", "bar"]'),
        )

        # remove upload interfaces from algorithm
        self.algorithm.inputs.remove(self.ci_img_upload, self.ci_json_file)

        job = AlgorithmJobFactory(
            algorithm_image=self.algorithm_image,
            algorithm_model=self.algorithm_model,
            status=Job.SUCCESS,
        )
        job.inputs.set([civ1, civ2, civ3, civ4])

        old_civ_count = ComponentInterfaceValue.objects.count()

        with patch(
            "grandchallenge.components.tasks.execute_job"
        ) as mocked_execute_job:
            # no need to actually execute the job,
            # all other async tasks should run though
            mocked_execute_job.return_value = None
            with self.captureOnCommitCallbacks(execute=True):
                response = get_view_for_user(
                    viewname="api:algorithms-job-list",
                    client=self.client,
                    method=self.client.post,
                    user=self.user,
                    follow=True,
                    content_type="application/json",
                    data={
                        "algorithm": self.algorithm.api_url,
                        "inputs": [
                            {"interface": self.ci_str.slug, "value": "Foo"},
                            {"interface": self.ci_bool.slug, "value": True},
                            {
                                "interface": self.ci_existing_img.slug,
                                "image": self.image_2.api_url,
                            },
                            {
                                "interface": self.ci_json_in_db_with_schema.slug,
                                "value": json.loads('["Foo", "bar"]'),
                            },
                        ],
                    },
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
    def test_create_job_with_faulty_inputs(self):
        # we just test 1 type of error here, validation for all interface kinds is
        # tested in
        with patch(
            "grandchallenge.components.tasks.execute_job"
        ) as mocked_execute_job:
            # no need to actually execute the job,
            # all other async tasks should run though
            mocked_execute_job.return_value = None
            with self.captureOnCommitCallbacks(execute=True):
                response = get_view_for_user(
                    viewname="api:algorithms-job-list",
                    client=self.client,
                    method=self.client.post,
                    user=self.user,
                    follow=True,
                    content_type="application/json",
                    data={
                        "algorithm": self.algorithm.api_url,
                        "inputs": [
                            {"interface": self.ci_str.slug, "value": None},
                            {"interface": self.ci_bool.slug, "value": True},
                            {
                                "interface": self.ci_img_upload.slug,
                                "upload_session": self.im_upload.api_url,
                            },
                            {
                                "interface": self.ci_existing_img.slug,
                                "image": self.image_2.api_url,
                            },
                            {
                                "interface": self.ci_json_file.slug,
                                "user_upload": self.file_upload.api_url,
                            },
                            {
                                "interface": self.ci_json_in_db_with_schema.slug,
                                "value": json.loads('["Foo", "bar"]'),
                            },
                        ],
                    },
                )

        assert response.status_code == 400
        assert "JSON does not fulfill schema" in str(response.content)

        assert Job.objects.count() == 0
        assert ComponentInterfaceValue.objects.count() == 0
