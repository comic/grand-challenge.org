import pytest

from grandchallenge.algorithms.models import DEFAULT_INPUT_INTERFACE_SLUG, Job
from grandchallenge.algorithms.tasks import (
    add_job_viewer_groups,
    create_algorithm_jobs,
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
        create_algorithm_jobs(algorithm_image=ai, images=[image])
        assert Job.objects.count() == 1

    def test_creates_job_correctly(self):
        ai = AlgorithmImageFactory()
        image = ImageFactory()
        assert Job.objects.count() == 0
        create_algorithm_jobs(algorithm_image=ai, images=[image])
        assert Job.objects.count() == 1
        j = Job.objects.first()
        assert j.algorithm_image == ai
        assert j.creator is None
        assert (
            j.inputs.get(interface__slug=DEFAULT_INPUT_INTERFACE_SLUG).image
            == image
        )

    def test_is_idempotent(self):
        ai = AlgorithmImageFactory()
        image = ImageFactory()
        assert Job.objects.count() == 0
        create_algorithm_jobs(algorithm_image=ai, images=[image])
        assert Job.objects.count() == 1
        create_algorithm_jobs(algorithm_image=ai, images=[image])
        assert Job.objects.count() == 1

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


@pytest.mark.django_db
def test_add_viewer_groups():
    job = AlgorithmJobFactory()
    groups = [GroupFactory(), GroupFactory(), GroupFactory()]

    group_pks = [g.pk for g in groups]
    add_job_viewer_groups(job.pk, group_pks)
    for g_pk in group_pks:
        assert job.viewer_groups.filter(pk=g_pk).exists()

    add_job_viewer_groups(job.pk, [group_pks[0]])
    assert job.viewer_groups.filter(pk=group_pks[0]).count() == 1
