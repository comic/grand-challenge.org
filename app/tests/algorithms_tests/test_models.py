from datetime import timedelta

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from grandchallenge.algorithms.models import Algorithm, Job
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKind,
)
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmJobFactory,
)


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

    with pytest.raises(ProtectedError):
        getattr(algorithm, group).delete()


@pytest.mark.django_db
def test_default_interfaces_created():
    a = AlgorithmFactory()

    assert {i.kind for i in a.inputs.all()} == {
        InterfaceKind.InterfaceKindChoices.IMAGE
    }
    assert {o.kind for o in a.outputs.all()} == {
        InterfaceKind.InterfaceKindChoices.ANY,
        InterfaceKind.InterfaceKindChoices.HEAT_MAP,
    }


@pytest.mark.django_db
def test_rendered_result_text():
    def create_result(jb, result: dict):
        interface = ComponentInterface.objects.get(slug="results-json-file")

        try:
            output_civ = jb.outputs.get(interface=interface)
            output_civ.value = result
            output_civ.save()
        except ObjectDoesNotExist:
            output_civ = ComponentInterfaceValue.objects.create(
                interface=interface, value=result
            )
            jb.outputs.add(output_civ)

    job = AlgorithmJobFactory()
    job.algorithm_image.algorithm.result_template = (
        "foo score: {{results.foo}}"
    )

    assert job.rendered_result_text == ""
    create_result(job, {"foo": 13.37})
    del job.rendered_result_text
    assert job.rendered_result_text == "<p>foo score: 13.37</p>"

    job.algorithm_image.algorithm.result_template = "{% for key, value in dict.metrics.items() -%}{{ key }}  {{ value }}{% endfor %}"
    del job.rendered_result_text
    assert job.rendered_result_text == "Jinja template is invalid"

    job.algorithm_image.algorithm.result_template = "{{ str.__add__('test')}}"
    del job.rendered_result_text
    assert job.rendered_result_text == "Jinja template is invalid"


@pytest.mark.django_db
def test_average_duration():
    alg = AlgorithmFactory()
    now = timezone.now()

    assert alg.average_duration is None

    j = AlgorithmJobFactory(algorithm_image__algorithm=alg)

    j.started_at = now - timedelta(minutes=5)
    j.completed_at = now
    j.status = j.SUCCESS
    j.save()

    assert alg.average_duration == timedelta(minutes=5)

    # Unsuccessful jobs should not count
    j = AlgorithmJobFactory(algorithm_image__algorithm=alg)
    j.started_at = now - timedelta(minutes=10)
    j.completed_at = now
    j.status = j.FAILURE
    j.save()

    assert alg.average_duration == timedelta(minutes=5)

    # Nor should jobs for other algorithms
    j = AlgorithmJobFactory()
    j.started_at = now - timedelta(minutes=15)
    j.completed_at = now
    j.status = j.SUCCESS
    j.save()

    assert alg.average_duration == timedelta(minutes=5)


class TestAlgorithmJobGroups(TestCase):
    def test_job_group_created(self):
        j = AlgorithmJobFactory()
        assert j.viewers is not None
        assert j.viewers.name.startswith("algorithms_job_")
        assert j.viewers.name.endswith("_viewers")

    def test_job_group_deletion(self):
        j = AlgorithmJobFactory()
        g = j.viewers

        Job.objects.filter(pk__in=[j.pk]).delete()

        with pytest.raises(ObjectDoesNotExist):
            g.refresh_from_db()

    def test_group_deletion_reverse(self):
        j = AlgorithmJobFactory()
        g = j.viewers

        with pytest.raises(ProtectedError):
            g.delete()

    def test_creator_in_viewers_group(self):
        j = AlgorithmJobFactory()
        assert {*j.viewers.user_set.all()} == {j.creator}

    def test_viewer_group_in_m2m(self):
        j = AlgorithmJobFactory()
        assert {*j.viewer_groups.all()} == {j.viewers}
