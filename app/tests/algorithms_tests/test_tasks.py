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
        ai = AlgorithmImageFactory()
        image = ImageFactory()
        user = UserFactory()
        image.origin.creator = user
        image.origin.save()
        create_algorithm_jobs(
            algorithm_image=ai, images=[image], session=image.origin
        )
        j = Job.objects.first()
        assert j.creator == user

    def test_extra_viewer_groups(self):
        ai = AlgorithmImageFactory()
        image = ImageFactory()
        groups = (GroupFactory(), GroupFactory(), GroupFactory())
        jobs = create_algorithm_jobs(
            algorithm_image=ai, images=[image], extra_viewer_groups=groups
        )
        for g in groups:
            assert jobs[0].viewer_groups.filter(pk=g.pk).exists()


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
