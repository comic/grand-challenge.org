import pytest
from django.contrib.sites.models import Site
from django.core import mail
from django.core.exceptions import ObjectDoesNotExist

from grandchallenge.algorithms.models import Algorithm, Job
from grandchallenge.components.models import InterfaceKindChoices
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.factories import ImageFactory, UserFactory


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


@pytest.mark.django_db
def test_default_interfaces_created():
    a = AlgorithmFactory()

    assert {i.kind for i in a.inputs.all()} == {InterfaceKindChoices.IMAGE}
    assert {o.kind for o in a.outputs.all()} == {
        InterfaceKindChoices.MULTIPLE_IMAGES,
        InterfaceKindChoices.JSON,
    }


@pytest.mark.django_db
def test_interface_value_is_set():
    job = AlgorithmJobFactory()

    inputs = job.inputs.all()

    assert len(inputs) == 1
    assert inputs[0].image == job.image


@pytest.mark.django_db
def test_interface_changes_with_image():
    job = AlgorithmJobFactory()

    old_image_pk = job.image.pk

    assert job.inputs.first().image.pk == old_image_pk
    assert job.inputs.first().image.pk == job.image.pk

    job.image = ImageFactory()
    job.save()
    job.refresh_from_db()

    assert job.image.pk != old_image_pk
    assert job.inputs.first().image.pk == job.image.pk
