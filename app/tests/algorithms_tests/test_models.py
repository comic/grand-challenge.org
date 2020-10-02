import pytest
from django.core.exceptions import ObjectDoesNotExist

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.components.models import InterfaceKindChoices
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

    getattr(algorithm, group).delete()

    with pytest.raises(ObjectDoesNotExist):
        users_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        editors_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        algorithm.refresh_from_db()


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

    job = AlgorithmJobFactory()
    job.algorithm_image.algorithm.result_template = (
        "foo score: {{result_dict.foo}}"
    )

    assert job.rendered_result_text == ""
    job.create_result(result={"foo": 13.37})
    assert job.rendered_result_text == "<p>foo score: 13.37</p>"

    job.algorithm_image.algorithm.result_template = "{% for key, value in dict.metrics.items() -%}{{ key }}  {{ value }}{% endfor %}"
    assert (
        job.rendered_result_text
        == "Jinja template is incorrect: 'type object' has no attribute 'metrics'"
    )

    job.algorithm_image.algorithm.result_template = "{{ str.__add__('test')}}"
    assert job.rendered_result_text == "Jinja template is not allowed"
