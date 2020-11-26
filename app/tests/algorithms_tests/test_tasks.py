import re

import pytest

from grandchallenge.algorithms.models import DEFAULT_INPUT_INTERFACE_SLUG, Job
from grandchallenge.algorithms.tasks import (
    create_algorithm_jobs,
    create_jobs_workflow,
)
from grandchallenge.components.models import ComponentInterface
from tests.algorithms_tests.factories import (
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.components_tests.factories import ComponentInterfaceValueFactory
from tests.factories import GroupFactory, ImageFactory, UserFactory


@pytest.mark.django_db
class TestCreateAlgorithmJobs:
    def test_no_algorithm_image_does_nothing(self):
        image = ImageFactory()
        create_algorithm_jobs(
            algorithm_image=None, images=[image], session=image.origin.pk
        )
        assert Job.objects.count() == 0

    def test_no_images_does_nothing(self):
        ai = AlgorithmImageFactory()
        create_algorithm_jobs(algorithm_image=ai, images=[])
        assert Job.objects.count() == 0

    def test_civ_existing_does_nothing(self):
        default_input_interface = ComponentInterface.objects.get(
            slug=DEFAULT_INPUT_INTERFACE_SLUG
        )
        image = ImageFactory()
        ai = AlgorithmImageFactory()
        j = AlgorithmJobFactory(creator=None, algorithm_image=ai)
        civ = ComponentInterfaceValueFactory(
            interface=default_input_interface, image=image
        )
        j.inputs.set([civ])
        assert Job.objects.count() == 1
        jobs = create_algorithm_jobs(algorithm_image=ai, images=[image])
        assert Job.objects.count() == 1
        assert len(jobs) == 0

    def test_creates_job_correctly(self):
        ai = AlgorithmImageFactory()
        image = ImageFactory()
        assert Job.objects.count() == 0
        jobs = create_algorithm_jobs(algorithm_image=ai, images=[image])
        assert Job.objects.count() == 1
        j = Job.objects.first()
        assert j.algorithm_image == ai
        assert j.creator is None
        assert (
            j.inputs.get(interface__slug=DEFAULT_INPUT_INTERFACE_SLUG).image
            == image
        )
        assert j.pk == jobs[0].pk

    def test_is_idempotent(self):
        ai = AlgorithmImageFactory()
        image = ImageFactory()
        assert Job.objects.count() == 0
        create_algorithm_jobs(algorithm_image=ai, images=[image])
        assert Job.objects.count() == 1
        jobs = create_algorithm_jobs(algorithm_image=ai, images=[image])
        assert Job.objects.count() == 1
        assert len(jobs) == 0

    def test_gets_creator_from_session(self):
        riu = RawImageUploadSessionFactory()
        riu.image_set.add(ImageFactory(), ImageFactory())
        create_algorithm_jobs(
            algorithm_image=riu.algorithm_image,
            images=riu.image_set.all(),
            session=riu,
        )
        j = Job.objects.first()
        assert j.creator == riu.creator

    def test_extra_viewer_groups(self):
        ai = AlgorithmImageFactory()
        image = ImageFactory()
        groups = (GroupFactory(), GroupFactory(), GroupFactory())
        jobs = create_algorithm_jobs(
            algorithm_image=ai, images=[image], extra_viewer_groups=groups
        )
        for g in groups:
            assert jobs[0].viewer_groups.filter(pk=g.pk).exists()

    def test_create_jobs_is_limited(self):
        user, editor = UserFactory(), UserFactory()

        def create_upload(upload_creator):
            riu = RawImageUploadSessionFactory()
            riu.algorithm_image.algorithm.credits_per_job = 400
            riu.algorithm_image.algorithm.add_editor(editor)
            riu.algorithm_image.algorithm.save()
            riu.creator = upload_creator

            for _ in range(3):
                ImageFactory(origin=riu),
            riu.save()
            return riu

        assert Job.objects.count() == 0

        # Create an upload session as editor; should not be limited
        upload = create_upload(editor)
        create_algorithm_jobs(
            algorithm_image=upload.algorithm_image,
            images=upload.image_set.all(),
            session=upload,
        )

        assert Job.objects.count() == 3

        # Create an upload session as user; should be limited
        upload_2 = create_upload(user)
        create_algorithm_jobs(
            algorithm_image=upload_2.algorithm_image,
            images=upload_2.image_set.all(),
            session=upload_2,
        )

        # An additional 2 jobs should be created (standard nr of credits is 1000
        # per user per month).
        assert Job.objects.count() == 5

        # As an editor you should not be limited
        upload_2.algorithm_image.algorithm.add_editor(user)
        upload_2.algorithm_image.algorithm.save()
        upload_2.save()

        # The job that was skipped on the previous run should now be accepted
        create_algorithm_jobs(
            algorithm_image=upload_2.algorithm_image,
            images=upload_2.image_set.all(),
            session=upload_2,
        )
        assert Job.objects.count() == 6


@pytest.mark.django_db
class TestCreateJobsWorkflow:
    def test_no_jobs_workflow(self):
        workflow = create_jobs_workflow([])
        assert (
            str(workflow)
            == "%grandchallenge.algorithms.tasks.send_failed_jobs_email((), job_pks=[], session_pk=None)"
        )

    def test_jobs_workflow(self):
        ai = AlgorithmImageFactory()
        images = [ImageFactory(), ImageFactory()]
        jobs = create_algorithm_jobs(algorithm_image=ai, images=images)
        workflow = create_jobs_workflow(jobs)
        pattern = re.compile(
            r"^%grandchallenge\.algorithms\.tasks\.send_failed_jobs_email\(\(grandchallenge\.components\.tasks\.execute_job\(job_pk=UUID\('[^']*'\), job_app_label='algorithms', job_model_name='job'\), grandchallenge\.components\.tasks\.execute_job\(job_pk=UUID\('[^']*'\), job_app_label='algorithms', job_model_name='job'\)\), job_pks=\[UUID\('[^']*'\), UUID\('[^']*'\)], session_pk=None\)$"
        )
        assert pattern.match(str(workflow))
