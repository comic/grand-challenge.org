import pytest

from grandchallenge.algorithms.models import Job
from grandchallenge.algorithms.tasks import create_algorithm_jobs
from tests.algorithms_tests.factories import AlgorithmImageFactory
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.factories import ImageFactory, UserFactory


@pytest.mark.django_db
def test_create_jobs_is_idempotent():
    image = ImageFactory()

    ai = AlgorithmImageFactory()
    user = UserFactory()
    image.origin.algorithm_image = ai
    image.origin.creator = user
    image.origin.save()

    assert Job.objects.count() == 0

    create_algorithm_jobs(upload_session_pk=image.origin.pk)

    assert Job.objects.count() == 1

    j = Job.objects.all()[0]
    assert j.algorithm_image == ai
    assert j.creator == user
    assert j.inputs.get(interface__slug="generic-medical-image").image == image

    # Running the job twice should not result in new jobs
    create_algorithm_jobs(upload_session_pk=image.origin.pk)

    assert Job.objects.count() == 1

    # Changing the algorithm image should create a new job
    image.origin.algorithm_image = AlgorithmImageFactory()
    image.origin.save()

    create_algorithm_jobs(upload_session_pk=image.origin.pk)

    assert Job.objects.count() == 2


@pytest.mark.django_db
def test_create_jobs_is_limited():
    user = UserFactory()
    riu = RawImageUploadSessionFactory()
    riu.algorithm_image.algorithm.job_limit = 2
    riu.algorithm_image.algorithm.save()
    riu.creator = user

    im1, im2, im3 = (
        ImageFactory(origin=riu),
        ImageFactory(origin=riu),
        ImageFactory(origin=riu),
    )
    riu.save()

    assert Job.objects.count() == 0

    create_algorithm_jobs(upload_session_pk=im1.origin.pk)

    # A maximum of 2 jobs should be created
    assert Job.objects.count() == 2
