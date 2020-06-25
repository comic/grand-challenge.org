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


@pytest.mark.django_db
def test_default_interfaces_created():
    a = AlgorithmFactory()

    assert {i.kind for i in a.inputs.all()} == {InterfaceKindChoices.IMAGE}
    assert {o.kind for o in a.outputs.all()} == {InterfaceKindChoices.JSON}


@pytest.mark.django_db
def test_outputs_are_set():
    j = AlgorithmJobFactory()
    j.create_result(result={"dsaf": 35421})

    outputs = j.outputs.all()
    assert len(outputs) == 1
    assert outputs[0].interface.kind == InterfaceKindChoices.JSON
    assert outputs[0].value == {"dsaf": 35421}

    job = AlgorithmJobFactory()
    job.create_result(result={"foo": 13.37})

    outputs = job.outputs.all()
    assert len(outputs) == 1
    assert outputs[0].interface.kind == InterfaceKindChoices.JSON
    assert outputs[0].value == {"foo": 13.37}

    job.create_result(result={"bar": 13.37})
    job.refresh_from_db()

    outputs = job.outputs.all()
    assert len(outputs) == 1
    assert outputs[0].interface.kind == InterfaceKindChoices.JSON
    assert outputs[0].value == {"bar": 13.37}

    # the original job should not be modified
    j.refresh_from_db()
    outputs = j.outputs.all()
    assert len(outputs) == 1
    assert outputs[0].interface.kind == InterfaceKindChoices.JSON
    assert outputs[0].value == {"dsaf": 35421}
