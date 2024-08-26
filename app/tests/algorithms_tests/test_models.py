import json
from datetime import datetime, timedelta, timezone

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils.timezone import now

from grandchallenge.algorithms.models import Algorithm, Job
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.credits.models import Credit
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
    AlgorithmModelFactory,
)
from tests.cases_tests import RESOURCE_PATH
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory
from tests.uploads_tests.factories import create_upload_from_file
from tests.utils import get_view_for_user


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
def test_no_default_interfaces_created():
    a = AlgorithmFactory()

    assert {i.kind for i in a.inputs.all()} == set()
    assert {o.kind for o in a.outputs.all()} == set()


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

    job = AlgorithmJobFactory(time_limit=60)
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

    j = AlgorithmJobFactory(
        algorithm_image__algorithm=alg, time_limit=alg.time_limit
    )

    j.started_at = start - timedelta(minutes=5)
    j.completed_at = start
    j.status = j.SUCCESS
    j.save()

    assert alg.average_duration == timedelta(minutes=5)

    # Unsuccessful jobs should not count
    j = AlgorithmJobFactory(
        algorithm_image__algorithm=alg, time_limit=alg.time_limit
    )
    j.started_at = start - timedelta(minutes=10)
    j.completed_at = start
    j.status = j.FAILURE
    j.save()

    assert alg.average_duration == timedelta(minutes=5)

    # Nor should jobs for other algorithms
    j = AlgorithmJobFactory(time_limit=60)
    j.started_at = start - timedelta(minutes=15)
    j.completed_at = start
    j.status = j.SUCCESS
    j.save()

    assert alg.average_duration == timedelta(minutes=5)


class TestAlgorithmJobGroups(TestCase):
    def test_job_group_created(self):
        j = AlgorithmJobFactory(time_limit=60)
        assert j.viewers is not None
        assert j.viewers.name.startswith("algorithms_job_")
        assert j.viewers.name.endswith("_viewers")

    def test_job_group_deletion(self):
        j = AlgorithmJobFactory(time_limit=60)
        g = j.viewers

        Job.objects.filter(pk__in=[j.pk]).delete()

        with pytest.raises(ObjectDoesNotExist):
            g.refresh_from_db()

    def test_group_deletion_reverse(self):
        j = AlgorithmJobFactory(time_limit=60)
        g = j.viewers

        with pytest.raises(ProtectedError):
            g.delete()

    def test_creator_in_viewers_group(self):
        j = AlgorithmJobFactory(time_limit=60)
        assert {*j.viewers.user_set.all()} == {j.creator}

    def test_viewer_group_in_m2m(self):
        j = AlgorithmJobFactory(time_limit=60)
        assert {*j.viewer_groups.all()} == {j.viewers}


def test_get_or_create_display_set_unsuccessful_job():
    j = AlgorithmJobFactory.build(time_limit=60)

    with pytest.raises(RuntimeError) as error:
        j.get_or_create_display_set(reader_study=None)

    assert "Display sets can only be created from successful jobs" in str(
        error
    )


@pytest.mark.django_db
def test_get_or_create_display_set():
    rs1, rs2 = ReaderStudyFactory.create_batch(2)
    j = AlgorithmJobFactory(status=Job.SUCCESS, time_limit=60)
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
    j = AlgorithmJobFactory(status=Job.SUCCESS, time_limit=60)
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
    j = AlgorithmJobFactory(status=Job.SUCCESS, time_limit=60)
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
    def test_limited_jobs_for_editors(self, client):
        alg1, alg2 = AlgorithmFactory.create_batch(2, credits_per_job=100)
        user1, user2, user3 = UserFactory.create_batch(3)
        alg1.add_editor(user=user1)
        alg1.add_editor(user=user2)
        alg2.add_editor(user=user1)

        ai = AlgorithmImageFactory(
            algorithm=alg1,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )

        # no jobs run by any editor yet
        assert ai.get_remaining_jobs(user=user1) == 15
        assert ai.get_remaining_jobs(user=user2) == 15
        # normal user gets standard credits
        assert ai.get_remaining_jobs(user=user3) == 10

        AlgorithmJobFactory.create_batch(
            4,
            creator=user1,
            algorithm_image=ai,
            time_limit=ai.algorithm.time_limit,
        )
        # limits apply to both editors
        assert ai.get_remaining_jobs(user=user1) == 11
        assert ai.get_remaining_jobs(user=user2) == 11

        # job limit is per algorithm image sha
        # uploading a new image resets editor credits
        ai2 = AlgorithmImageFactory(
            algorithm=alg1,
            is_manifest_valid=True,
            is_in_registry=True,
        )
        get_view_for_user(
            viewname="algorithms:image-activate",
            client=client,
            method=client.post,
            reverse_kwargs={"slug": alg1.slug},
            data={"algorithm_image": ai2.pk},
            user=user1,
            follow=True,
        )
        ai2.refresh_from_db()

        assert ai2.get_remaining_jobs(user=user1) == 15
        assert ai2.get_remaining_jobs(user=user2) == 15

        AlgorithmJobFactory(
            creator=user1,
            algorithm_image=ai2,
            time_limit=ai2.algorithm.time_limit,
        )
        assert ai2.get_remaining_jobs(user=user1) == 14
        assert ai2.get_remaining_jobs(user=user2) == 14

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
        ai = AlgorithmImageFactory(
            algorithm=algorithm,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )

        user_credit = Credit.objects.get(user=user)
        user_credit.credits = user_credits
        user_credit.save()

        assert ai.get_remaining_jobs(user=user) == expected_jobs

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
        ai = AlgorithmImageFactory(
            algorithm=algorithm,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )

        algorithm2 = AlgorithmFactory(credits_per_job=credits_per_job)

        AlgorithmJobFactory(
            algorithm_image__algorithm=algorithm,
            creator=None,
            time_limit=algorithm.time_limit,
        )
        AlgorithmJobFactory(
            algorithm_image__algorithm=algorithm,
            creator=user,
            time_limit=algorithm.time_limit,
        )
        AlgorithmJobFactory(
            algorithm_image__algorithm=algorithm2,
            creator=user,
            time_limit=algorithm2.time_limit,
        )

        user_credit = Credit.objects.get(user=user)
        user_credit.credits = user_credits
        user_credit.save()

        assert ai.get_remaining_jobs(user=user) == expected_jobs


@pytest.mark.django_db()
def test_user_statistics():
    algorithm_image = AlgorithmImageFactory()

    u1, u2, _ = UserFactory.create_batch(3)

    AlgorithmJobFactory(time_limit=60)
    AlgorithmJobFactory(
        algorithm_image=algorithm_image,
        creator=None,
        time_limit=algorithm_image.algorithm.time_limit,
    )
    AlgorithmJobFactory(
        algorithm_image=algorithm_image,
        creator=u1,
        time_limit=algorithm_image.algorithm.time_limit,
    )
    AlgorithmJobFactory(
        algorithm_image=algorithm_image,
        creator=u1,
        time_limit=algorithm_image.algorithm.time_limit,
    )
    AlgorithmJobFactory(creator=u1, time_limit=60)
    AlgorithmJobFactory(
        algorithm_image=algorithm_image,
        creator=u2,
        time_limit=algorithm_image.algorithm.time_limit,
    )

    assert {
        user.pk: user.job_count
        for user in algorithm_image.algorithm.user_statistics
    } == {u1.pk: 2, u2.pk: 1}


@pytest.mark.django_db
def test_usage_statistics():
    algorithm_image = AlgorithmImageFactory()

    AlgorithmJobFactory(
        time_limit=60
    )  # for another job, should not be included in stats

    for year, month, status in (
        (2020, 1, Job.SUCCESS),
        (2020, 1, Job.PENDING),
        (2020, 1, Job.CANCELLED),
        (2020, 2, Job.SUCCESS),
        (2022, 1, Job.SUCCESS),
        (2022, 1, Job.SUCCESS),
    ):
        job = AlgorithmJobFactory(
            algorithm_image=algorithm_image,
            time_limit=algorithm_image.algorithm.time_limit,
        )
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


@pytest.mark.parametrize(
    "string, bool, new_image, new_file, civs_in_output",
    [
        ("foo", True, True, True, [1, 0, 0, 0]),
        ("foo1", False, True, True, [0, 1, 0, 0]),
        ("foo1", True, False, True, [0, 0, 1, 0]),
        ("foo1", True, True, False, [0, 0, 0, 1]),
    ],
)
@pytest.mark.django_db
def test_retrieve_existing_civs(
    string, bool, new_image, new_file, civs_in_output
):
    ci_str = ComponentInterfaceFactory(kind=ComponentInterface.Kind.STRING)
    ci_bool = ComponentInterfaceFactory(kind=ComponentInterface.Kind.BOOL)
    ci_im = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)
    ci_file = ComponentInterfaceFactory(kind=ComponentInterface.Kind.PDF)

    old_im = ImageFactory()
    old_file = ContentFile(json.dumps(True).encode("utf-8"), name="test.json")

    if new_file:
        upload = create_upload_from_file(
            creator=UserFactory(), file_path=RESOURCE_PATH / "test.pdf"
        )
    if new_image:
        upload_session = RawImageUploadSessionFactory()

    list_of_civs = [
        ComponentInterfaceValueFactory(interface=ci_str, value="foo"),
        ComponentInterfaceValueFactory(interface=ci_bool, value=False),
        ComponentInterfaceValueFactory(interface=ci_im, image=old_im),
        ComponentInterfaceValueFactory(interface=ci_file, file=old_file),
    ]

    data = {
        ci_str.slug: string,
        ci_bool.slug: bool,
        ci_im.slug: upload_session.api_url if new_image else old_im,
        ci_file.slug: upload.api_url if new_file else list_of_civs[3],
    }

    civs = Job.objects.retrieve_existing_civs(civ_data=data)

    assert civs == [
        item
        for item, flag in zip(list_of_civs, civs_in_output, strict=True)
        if flag == 1
    ]


@pytest.mark.django_db
class TestGetJobsWithSameInputs(TestCase):
    def setUp(self):
        self.alg = AlgorithmFactory()
        self.ci1, self.ci2 = ComponentInterfaceFactory.create_batch(
            2, kind=ComponentInterface.Kind.STRING
        )
        self.alg.inputs.set([self.ci1, self.ci2])

        self.ai = AlgorithmImageFactory(algorithm=self.alg)
        self.am = AlgorithmModelFactory(algorithm=self.alg)

        self.data = {self.ci1.slug: "foo", self.ci2.slug: "bar"}
        self.civs = [
            ComponentInterfaceValueFactory(interface=self.ci1, value="foo"),
            ComponentInterfaceValueFactory(interface=self.ci2, value="bar"),
        ]

    def test_job_with_same_image_different_model(self):
        j = AlgorithmJobFactory(algorithm_image=self.ai, time_limit=10)
        j.inputs.set(self.civs)
        jobs = Job.objects.get_jobs_with_same_inputs(
            data=self.data, algorithm_image=self.ai, algorithm_model=self.am
        )
        assert len(jobs) == 0

    def test_job_with_same_model_different_image(self):
        j = AlgorithmJobFactory(
            algorithm_image=AlgorithmImageFactory(),
            algorithm_model=self.am,
            time_limit=10,
        )
        j.inputs.set(self.civs)
        jobs = Job.objects.get_jobs_with_same_inputs(
            data=self.data, algorithm_image=self.ai, algorithm_model=self.am
        )
        assert len(jobs) == 0

    def test_job_with_same_model_and_image(self):
        j = AlgorithmJobFactory(
            algorithm_model=self.am, algorithm_image=self.ai, time_limit=10
        )
        j.inputs.set(self.civs)
        jobs = Job.objects.get_jobs_with_same_inputs(
            data=self.data, algorithm_image=self.ai, algorithm_model=self.am
        )
        assert len(jobs) == 1
        assert j in jobs

    def test_job_with_different_image_and_model(self):
        j = AlgorithmJobFactory(
            algorithm_model=AlgorithmModelFactory(),
            algorithm_image=AlgorithmImageFactory(),
            time_limit=10,
        )
        j.inputs.set(self.civs)
        jobs = Job.objects.get_jobs_with_same_inputs(
            data=self.data, algorithm_image=self.ai, algorithm_model=self.am
        )
        assert len(jobs) == 0

    def test_job_with_same_image_no_model_provided(self):
        j = AlgorithmJobFactory(
            algorithm_model=self.am, algorithm_image=self.ai, time_limit=10
        )
        j.inputs.set(self.civs)
        jobs = Job.objects.get_jobs_with_same_inputs(
            data=self.data, algorithm_image=self.ai, algorithm_model=None
        )
        assert len(jobs) == 0

    def test_job_with_same_image_and_without_model(self):
        j = AlgorithmJobFactory(algorithm_image=self.ai, time_limit=10)
        j.inputs.set(self.civs)
        jobs = Job.objects.get_jobs_with_same_inputs(
            data=self.data, algorithm_image=self.ai, algorithm_model=None
        )
        assert j in jobs
        assert len(jobs) == 1

    def test_job_with_different_input(self):
        j = AlgorithmJobFactory(algorithm_image=self.ai, time_limit=10)
        j.inputs.set(
            [
                ComponentInterfaceValueFactory(),
                ComponentInterfaceValueFactory(),
            ]
        )
        jobs = Job.objects.get_jobs_with_same_inputs(
            data=self.data, algorithm_image=self.ai, algorithm_model=None
        )
        assert len(jobs) == 0


@pytest.mark.django_db
def test_is_complimentary_set_for_editors():
    u = UserFactory()
    a = AlgorithmFactory()

    a.add_editor(user=u)
    j = AlgorithmJobFactory(
        algorithm_image__algorithm=a, creator=u, time_limit=60
    )

    assert j.is_complimentary is True


@pytest.mark.django_db
def test_is_complimentary_not_set_for_normal_user():
    u = UserFactory()
    a = AlgorithmFactory()

    j = AlgorithmJobFactory(
        algorithm_image__algorithm=a, creator=u, time_limit=60
    )

    assert j.is_complimentary is False


@pytest.mark.django_db
def test_is_complimentary_not_set_for_none_user():
    a = AlgorithmFactory()

    j = AlgorithmJobFactory(
        algorithm_image__algorithm=a, creator=None, time_limit=60
    )

    assert j.is_complimentary is False


@pytest.mark.django_db
def test_is_complimentary_limited_by_free_jobs(settings):
    settings.ALGORITHM_IMAGES_COMPLIMENTARY_EDITOR_JOBS = 2

    u1, u2, u3 = UserFactory.create_batch(3)
    ai = AlgorithmImageFactory()

    ai.algorithm.add_editor(user=u1)
    ai.algorithm.add_editor(user=u2)
    ai.algorithm.add_user(user=u3)

    j_none_user = AlgorithmJobFactory(
        algorithm_image=ai, creator=None, time_limit=60
    )
    j_other_user = AlgorithmJobFactory(
        algorithm_image=ai, creator=u3, time_limit=60
    )

    assert ai.get_remaining_complimentary_jobs(user=u1) == 2
    assert ai.get_remaining_complimentary_jobs(user=u2) == 2
    assert ai.get_remaining_complimentary_jobs(user=u3) == 0

    j_u1 = AlgorithmJobFactory(algorithm_image=ai, creator=u1, time_limit=60)

    assert ai.get_remaining_complimentary_jobs(user=u1) == 1
    assert ai.get_remaining_complimentary_jobs(user=u2) == 1
    assert ai.get_remaining_complimentary_jobs(user=u3) == 0

    j_u2 = AlgorithmJobFactory(algorithm_image=ai, creator=u2, time_limit=60)
    j2_u2 = AlgorithmJobFactory(algorithm_image=ai, creator=u2, time_limit=60)

    assert j_none_user.is_complimentary is False
    assert j_other_user.is_complimentary is False
    assert j_u1.is_complimentary is True
    assert j_u2.is_complimentary is True
    assert j2_u2.is_complimentary is False


@pytest.mark.django_db
def test_other_algorithm_images_not_considered(settings):
    settings.ALGORITHM_IMAGES_COMPLIMENTARY_EDITOR_JOBS = 1

    u = UserFactory()
    ai1, ai2 = AlgorithmImageFactory.create_batch(2)

    ai1.algorithm.add_editor(user=u)
    ai2.algorithm.add_editor(user=u)

    ai1_j1 = AlgorithmJobFactory(algorithm_image=ai1, creator=u, time_limit=60)
    ai1_j2 = AlgorithmJobFactory(algorithm_image=ai1, creator=u, time_limit=60)
    ai2_j1 = AlgorithmJobFactory(algorithm_image=ai2, creator=u, time_limit=60)
    ai2_j2 = AlgorithmJobFactory(algorithm_image=ai2, creator=u, time_limit=60)

    assert ai1_j1.is_complimentary is True
    assert ai1_j2.is_complimentary is False
    assert ai2_j1.is_complimentary is True
    assert ai2_j2.is_complimentary is False


@pytest.mark.django_db
def test_remaining_complimentary_jobs(settings):
    u = UserFactory()
    ai = AlgorithmImageFactory()

    ai.algorithm.add_editor(user=u)

    AlgorithmJobFactory(algorithm_image=ai, time_limit=60, creator=None)

    assert (
        ai.get_remaining_complimentary_jobs(user=u)
        == settings.ALGORITHM_IMAGES_COMPLIMENTARY_EDITOR_JOBS
    )

    AlgorithmJobFactory.create_batch(
        settings.ALGORITHM_IMAGES_COMPLIMENTARY_EDITOR_JOBS + 1,
        algorithm_image=ai,
        time_limit=60,
        creator=u,
    )

    assert ai.get_remaining_complimentary_jobs(user=u) == 0


@pytest.mark.django_db
def test_get_remaining_non_complimentary_jobs(settings):
    settings.ALGORITHM_IMAGES_COMPLIMENTARY_EDITOR_JOBS = 1

    # Check the default, the rest are assuming this
    assert Credit._meta.get_field("credits").get_default() == 1000

    credits_per_job = 300

    u = UserFactory()
    ai = AlgorithmImageFactory(algorithm__credits_per_job=credits_per_job)

    assert ai.get_remaining_non_complimentary_jobs(user=u) == 3
    assert ai.get_remaining_complimentary_jobs(user=u) == 0
    assert ai.get_remaining_jobs(user=u) == 3

    AlgorithmJobFactory(algorithm_image=ai, creator=u, time_limit=60)

    assert ai.get_remaining_non_complimentary_jobs(user=u) == 2
    assert ai.get_remaining_complimentary_jobs(user=u) == 0
    assert ai.get_remaining_jobs(user=u) == 2

    ai.algorithm.add_editor(user=u)

    AlgorithmJobFactory(algorithm_image=ai, creator=u, time_limit=60)

    assert ai.get_remaining_non_complimentary_jobs(user=u) == 2
    assert ai.get_remaining_complimentary_jobs(user=u) == 0
    assert ai.get_remaining_jobs(user=u) == 2

    AlgorithmJobFactory(algorithm_image=ai, creator=u, time_limit=60)

    assert ai.get_remaining_non_complimentary_jobs(user=u) == 1
    assert ai.get_remaining_complimentary_jobs(user=u) == 0
    assert ai.get_remaining_jobs(user=u) == 1

    # Overspend
    AlgorithmJobFactory.create_batch(
        2, algorithm_image=ai, creator=u, time_limit=60
    )

    assert ai.get_remaining_non_complimentary_jobs(user=u) == 0
    assert ai.get_remaining_complimentary_jobs(user=u) == 0
    assert ai.get_remaining_jobs(user=u) == 0


@pytest.mark.django_db
def test_non_editor_remaining_jobs():
    # Check the default, the rest are assuming this
    assert Credit._meta.get_field("credits").get_default() == 1000

    credits_per_job = 300

    u = UserFactory()
    ai = AlgorithmImageFactory(algorithm__credits_per_job=credits_per_job)

    AlgorithmJobFactory(algorithm_image=ai, creator=u, time_limit=60)

    assert ai.get_remaining_jobs(user=u) == 2

    ai.algorithm.add_editor(user=u)

    assert ai.get_remaining_jobs(user=u) == 7


@pytest.mark.django_db
def test_inputs_complete():
    alg = AlgorithmFactory()
    ci1, ci2, ci3 = ComponentInterfaceFactory.create_batch(
        3, kind=ComponentInterface.Kind.STRING
    )
    alg.inputs.set([ci1, ci2, ci3])
    job = AlgorithmJobFactory(algorithm_image__algorithm=alg, time_limit=10)

    civ_with_value_1 = ComponentInterfaceValueFactory(
        interface=ci1, value="Foo"
    )
    civ_with_value_2 = ComponentInterfaceValueFactory(
        interface=ci2, value="Bar"
    )
    civ_with_value_3 = ComponentInterfaceValueFactory(
        interface=ci3, value="Test"
    )
    civ_without_value = ComponentInterfaceValueFactory(
        interface=ci3, value=None
    )

    job.inputs.set([civ_with_value_1, civ_with_value_2, civ_without_value])
    assert not job.inputs_complete

    job.inputs.set(
        [
            civ_with_value_1,
            civ_with_value_2,
        ]
    )
    del job.inputs_complete
    assert not job.inputs_complete

    job.inputs.set([civ_with_value_1, civ_with_value_2, civ_with_value_3])
    del job.inputs_complete
    assert job.inputs_complete
