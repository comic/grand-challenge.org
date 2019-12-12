import pytest
from django.contrib.sites.models import Site
from django.core import mail
from django.core.exceptions import ObjectDoesNotExist

from grandchallenge.algorithms.models import Algorithm, Job
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.factories import UserFactory


@pytest.mark.django_db
def test_group_deletion():
    algorithm = AlgorithmFactory()
    users_group = algorithm.users_group
    editors_group = algorithm.editors_group

    assert users_group
    assert editors_group

    Algorithm.objects.filter(pk__in=[algorithm.pk]).delete()

    with pytest.raises(ObjectDoesNotExist):
        users_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        editors_group.refresh_from_db()


@pytest.mark.django_db
@pytest.mark.parametrize("group", ["users_group", "editors_group"])
def test_group_deletion_reverse(group):
    algorithm = AlgorithmFactory()
    users_group = algorithm.users_group
    editors_group = algorithm.editors_group

    assert users_group
    assert editors_group

    getattr(algorithm, group).delete()

    with pytest.raises(ObjectDoesNotExist):
        users_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        editors_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        algorithm.refresh_from_db()


@pytest.mark.django_db
def test_algorithm_job_update_status():
    alg = AlgorithmFactory()
    user = UserFactory()
    editor = UserFactory()

    alg.add_user(user)
    alg.add_editor(editor)

    ai = AlgorithmImageFactory(algorithm=alg)
    job = AlgorithmJobFactory(algorithm_image=ai, creator=user)

    for status, _ in Job.STATUS_CHOICES:
        job.update_status(status=status)
        job.refresh_from_db()
        assert job.status == status

    remaining_recipients = {user.email, editor.email}
    for email in mail.outbox:
        remaining_recipients -= set(email.to)
        assert (
            email.subject
            == f"[{Site.objects.get_current().domain.lower()}] [{alg.title.lower()}] Job Failed"
        )
        assert (
            f"Unfortunately your job for algorithm '{alg.title}' failed with an error"
            in email.body
        )
    assert remaining_recipients == set()
