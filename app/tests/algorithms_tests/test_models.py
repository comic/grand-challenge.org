from datetime import datetime, timedelta, timezone

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils.timezone import now

from grandchallenge.algorithms.models import Algorithm, Job
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKind,
)
from grandchallenge.credits.models import Credit
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.components_tests.factories import ComponentInterfaceValueFactory
from tests.factories import UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory


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
    start = now()

    assert alg.average_duration is None

    j = AlgorithmJobFactory(algorithm_image__algorithm=alg)

    j.started_at = start - timedelta(minutes=5)
    j.completed_at = start
    j.status = j.SUCCESS
    j.save()

    assert alg.average_duration == timedelta(minutes=5)

    # Unsuccessful jobs should not count
    j = AlgorithmJobFactory(algorithm_image__algorithm=alg)
    j.started_at = start - timedelta(minutes=10)
    j.completed_at = start
    j.status = j.FAILURE
    j.save()

    assert alg.average_duration == timedelta(minutes=5)

    # Nor should jobs for other algorithms
    j = AlgorithmJobFactory()
    j.started_at = start - timedelta(minutes=15)
    j.completed_at = start
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


def test_get_or_create_display_set_unsuccessful_job():
    j = AlgorithmJobFactory.build()

    with pytest.raises(RuntimeError) as error:
        j.get_or_create_display_set(reader_study=None)

    assert "Display sets can only be created from successful jobs" in str(
        error
    )


@pytest.mark.django_db
def test_get_or_create_display_set():
    rs1, rs2 = ReaderStudyFactory.create_batch(2)
    j = AlgorithmJobFactory(status=Job.SUCCESS)
    civ1, civ2, civ3 = ComponentInterfaceValueFactory.create_batch(3)
    j.inputs.set([civ1])
    j.outputs.set([civ2, civ3])

    new_display_set = j.get_or_create_display_set(reader_study=rs1)

    # Display set should be created with the correct values
    assert {*new_display_set.values.all()} == {civ1, civ2, civ3}
    # For the correct readerstudy
    assert new_display_set.reader_study == rs1

    # And is idempotent
    assert j.get_or_create_display_set(reader_study=rs1) == new_display_set

    assert rs1.display_sets.count() == 1
    assert rs2.display_sets.count() == 0


@pytest.mark.django_db
def test_new_display_set_created_on_output_change():
    rs = ReaderStudyFactory()
    j = AlgorithmJobFactory(status=Job.SUCCESS)
    civ1, civ2, civ3 = ComponentInterfaceValueFactory.create_batch(3)
    j.inputs.set([civ1])
    j.outputs.set([civ2])

    ds1 = j.get_or_create_display_set(reader_study=rs)

    # Display set should be created with the correct values
    assert {*ds1.values.all()} == {civ1, civ2}

    # A new display set should be created if the output changes
    j.outputs.add(civ3)
    ds2 = j.get_or_create_display_set(reader_study=rs)
    assert ds2 != ds1
    assert {*ds1.values.all()} == {civ1, civ2}
    assert {*ds2.values.all()} == {civ1, civ2, civ3}

    assert rs.display_sets.count() == 2


@pytest.mark.django_db
def test_new_display_set_created_on_reader_study_change():
    rs1, rs2 = ReaderStudyFactory.create_batch(2)
    j = AlgorithmJobFactory(status=Job.SUCCESS)
    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(2)
    j.inputs.set([civ1])
    j.outputs.set([civ2])

    ds1 = j.get_or_create_display_set(reader_study=rs1)

    # Display set should be created with the correct values
    assert {*ds1.values.all()} == {civ1, civ2}

    # A new display set should be created if the reader study changes
    ds2 = j.get_or_create_display_set(reader_study=rs2)
    assert ds2 != ds1
    assert {*ds1.values.all()} == {civ1, civ2}
    assert {*ds2.values.all()} == {civ1, civ2}

    assert rs1.display_sets.count() == 1
    assert rs2.display_sets.count() == 1


@pytest.mark.django_db
class TestJobLimits:
    def test_unlimited_jobs(self):
        algorithm = AlgorithmFactory(credits_per_job=100)
        user = UserFactory()

        assert algorithm.get_jobs_limit(user=user) is not None

        algorithm.add_editor(user=user)

        assert algorithm.get_jobs_limit(user=user) is None

    @pytest.mark.parametrize(
        "credits_per_job,user_credits,expected_jobs",
        (
            (100, 0, 0),
            (100, 50, 0),
            (100, 200, 2),
            (0, 100, 100),
        ),
    )
    def test_limited_jobs(self, credits_per_job, user_credits, expected_jobs):
        algorithm = AlgorithmFactory(credits_per_job=credits_per_job)
        user = UserFactory()

        user_credit = Credit.objects.get(user=user)
        user_credit.credits = user_credits
        user_credit.save()

        assert algorithm.get_jobs_limit(user=user) == expected_jobs

    @pytest.mark.parametrize(
        "credits_per_job,user_credits,expected_jobs",
        (
            (100, 0, 0),
            (100, 50, 0),
            (100, 200, 0),
            (0, 100, 100),
            (1, 100, 98),
        ),
    )
    def test_limited_jobs_with_existing(
        self, credits_per_job, user_credits, expected_jobs
    ):
        algorithm = AlgorithmFactory(credits_per_job=credits_per_job)
        user = UserFactory()

        algorithm2 = AlgorithmFactory(credits_per_job=credits_per_job)

        AlgorithmJobFactory(algorithm_image__algorithm=algorithm, creator=None)
        AlgorithmJobFactory(algorithm_image__algorithm=algorithm, creator=user)
        AlgorithmJobFactory(
            algorithm_image__algorithm=algorithm2, creator=user
        )

        user_credit = Credit.objects.get(user=user)
        user_credit.credits = user_credits
        user_credit.save()

        assert algorithm.get_jobs_limit(user=user) == expected_jobs


@pytest.mark.django_db()
def test_user_statistics():
    algorithm_image = AlgorithmImageFactory()

    u1, u2, _ = UserFactory.create_batch(3)

    AlgorithmJobFactory()
    AlgorithmJobFactory(algorithm_image=algorithm_image, creator=None)
    AlgorithmJobFactory(algorithm_image=algorithm_image, creator=u1)
    AlgorithmJobFactory(algorithm_image=algorithm_image, creator=u1)
    AlgorithmJobFactory(creator=u1)
    AlgorithmJobFactory(algorithm_image=algorithm_image, creator=u2)

    assert {
        user.pk: user.job_count
        for user in algorithm_image.algorithm.user_statistics
    } == {u1.pk: 2, u2.pk: 1}


@pytest.mark.django_db
def test_usage_statistics():
    algorithm_image = AlgorithmImageFactory()

    AlgorithmJobFactory()  # for another job, should not be included in stats

    for year, month, status in (
        (2020, 1, Job.SUCCESS),
        (2020, 1, Job.PENDING),
        (2020, 1, Job.CANCELLED),
        (2020, 2, Job.SUCCESS),
        (2022, 1, Job.SUCCESS),
        (2022, 1, Job.SUCCESS),
    ):
        job = AlgorithmJobFactory(algorithm_image=algorithm_image)
        job.created = datetime(year, month, 1, tzinfo=timezone.utc)
        job.status = status
        job.save()

    assert algorithm_image.algorithm.usage_chart == {
        "totals": {
            "Cancelled": 1,
            "Failed": 0,
            "Succeeded": 4,
        },
        "chart": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "width": "container",
            "padding": 0,
            "title": "Algorithm Usage",
            "data": {
                "values": [
                    {
                        "Status": "Succeeded",
                        "Month": "2020-01-01T00:00:00",
                        "Jobs Count": 1,
                    },
                    {
                        "Status": "Cancelled",
                        "Month": "2020-01-01T00:00:00",
                        "Jobs Count": 1,
                    },
                    {
                        "Status": "Succeeded",
                        "Month": "2020-02-01T00:00:00",
                        "Jobs Count": 1,
                    },
                    {
                        "Status": "Succeeded",
                        "Month": "2022-01-01T00:00:00",
                        "Jobs Count": 2,
                    },
                ]
            },
            "mark": "bar",
            "encoding": {
                "x": {
                    "field": "Month",
                    "type": "temporal",
                    "timeUnit": "yearmonth",
                },
                "y": {
                    "field": "Jobs Count",
                    "type": "quantitative",
                    "stack": True,
                },
                "tooltip": [
                    {
                        "field": "Month",
                        "type": "temporal",
                        "timeUnit": "yearmonth",
                    },
                    {"field": "Status", "type": "nominal"},
                    {"field": "Jobs Count", "type": "quantitative"},
                ],
                "color": {
                    "field": "Status",
                    "scale": {"domain": ["Succeeded", "Cancelled", "Failed"]},
                    "type": "nominal",
                },
            },
        },
    }
