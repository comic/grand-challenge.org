import json
from datetime import datetime, timedelta, timezone

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils.timezone import now

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmAlgorithmInterface,
    AlgorithmInterface,
    AlgorithmUserCredit,
    Job,
    get_existing_interface_for_inputs_and_outputs,
)
from grandchallenge.components.models import CIVData, ComponentInterface
from grandchallenge.components.schemas import GPUTypeChoices
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmInterfaceFactory,
    AlgorithmJobFactory,
    AlgorithmModelFactory,
    AlgorithmUserCreditFactory,
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
def test_average_duration(settings, django_capture_on_commit_callbacks):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    alg = AlgorithmFactory()

    assert alg.average_duration is None

    j = AlgorithmJobFactory(
        algorithm_image__algorithm=alg, time_limit=alg.time_limit
    )

    with django_capture_on_commit_callbacks(execute=True):
        j.update_status(status=j.SUCCESS, duration=timedelta(minutes=5))

    alg.refresh_from_db()
    assert alg.average_duration == timedelta(minutes=5)

    # Unsuccessful jobs should not count
    j = AlgorithmJobFactory(
        algorithm_image__algorithm=alg, time_limit=alg.time_limit
    )

    with django_capture_on_commit_callbacks(execute=True):
        j.update_status(status=j.FAILURE, duration=timedelta(minutes=10))

    alg.refresh_from_db()
    assert alg.average_duration == timedelta(minutes=5)

    # Nor should jobs for other algorithms
    j = AlgorithmJobFactory(time_limit=60)

    with django_capture_on_commit_callbacks(execute=True):
        j.update_status(status=j.SUCCESS, duration=timedelta(minutes=15))

    alg.refresh_from_db()
    assert alg.average_duration == timedelta(minutes=5)


@pytest.mark.django_db
class TestAlgorithmJobGroups:
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
        g.delete()

        j.refresh_from_db()

        assert j.viewers is None

    def test_creator_in_viewers_group(self):
        j = AlgorithmJobFactory(time_limit=60)
        assert {*j.viewers.user_set.all()} == {j.creator}

    def test_viewer_group_in_m2m(self):
        j = AlgorithmJobFactory(time_limit=60)

        assert j.viewers is not None
        assert {*j.viewer_groups.all()} == {j.viewers}

    def test_no_group_with_no_creator(self):
        j = AlgorithmJobFactory(creator=None, time_limit=60)

        assert j.viewers is None
        assert {*j.viewer_groups.all()} == set()


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
        alg1, alg2 = AlgorithmFactory.create_batch(
            2, minimum_credits_per_job=100, time_limit=60
        )
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
        "minimum_credits_per_job,user_credits,expected_jobs",
        (
            (100, 0, 0),
            (100, 50, 0),
            (100, 200, 2),
            # Uses system minimum credits per job (20)
            (0, 100, 5),
        ),
    )
    def test_limited_jobs(
        self, minimum_credits_per_job, user_credits, expected_jobs
    ):
        algorithm = AlgorithmFactory(
            minimum_credits_per_job=minimum_credits_per_job, time_limit=60
        )
        user = UserFactory()
        ai = AlgorithmImageFactory(
            algorithm=algorithm,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )

        AlgorithmUserCredit.objects.create(
            user=user,
            algorithm=ai.algorithm,
            credits=user_credits,
            valid_from=now().date(),
            valid_until=now().date(),
            comment="test",
        )

        assert ai.get_remaining_jobs(user=user) == expected_jobs

    @pytest.mark.parametrize(
        "minimum_credits_per_job,user_credits,expected_jobs",
        (
            (100, 0, 0),
            (100, 50, 0),
            (100, 100, 0),
            (100, 200, 1),
            (0, 100, 4),
            (30, 100, 2),
        ),
    )
    def test_limited_jobs_with_existing(
        self, minimum_credits_per_job, user_credits, expected_jobs
    ):
        algorithm = AlgorithmFactory(
            minimum_credits_per_job=minimum_credits_per_job, time_limit=60
        )
        user = UserFactory()
        ai = AlgorithmImageFactory(
            algorithm=algorithm,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )

        algorithm2 = AlgorithmFactory(
            minimum_credits_per_job=minimum_credits_per_job, time_limit=60
        )

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

        AlgorithmUserCredit.objects.create(
            user=user,
            algorithm=ai.algorithm,
            credits=user_credits,
            valid_from=now().date(),
            valid_until=now().date(),
            comment="test",
        )

        assert ai.get_remaining_jobs(user=user) == expected_jobs

    @pytest.mark.parametrize(
        "time_limit,expected_credits_per_job",
        (
            (100, 20),
            (2000, 60),
            (12000, 370),
        ),
    )
    def test_credits_vary_with_time_limit(
        self, time_limit, expected_credits_per_job
    ):
        algorithm = AlgorithmFactory(time_limit=time_limit)
        AlgorithmImageFactory(
            algorithm=algorithm,
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )

        assert algorithm.credits_per_job == expected_credits_per_job


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
    ci_im = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.PANIMG_IMAGE
    )
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
        CIVData(interface_slug=ci_str.slug, value=string),
        CIVData(interface_slug=ci_bool.slug, value=bool),
        CIVData(
            interface_slug=ci_im.slug,
            value=upload_session if new_image else old_im,
        ),
        CIVData(
            interface_slug=ci_file.slug,
            value=upload if new_file else list_of_civs[3],
        ),
    }

    civs = Job.objects.retrieve_existing_civs(civ_data_objects=data)

    assert civs == [
        item
        for item, flag in zip(list_of_civs, civs_in_output, strict=True)
        if flag == 1
    ]


@pytest.mark.django_db
class TestGetJobsWithSameInputs:

    def get_civ_data(self, civs):
        return [
            CIVData(interface_slug=civ.interface.slug, value=civ.value)
            for civ in civs
        ]

    def test_job_with_same_image_different_model(
        self, algorithm_with_image_and_model_and_two_inputs
    ):
        alg = algorithm_with_image_and_model_and_two_inputs.algorithm
        civs = algorithm_with_image_and_model_and_two_inputs.civs
        data = self.get_civ_data(civs=civs)

        j = AlgorithmJobFactory(
            algorithm_image=alg.active_image,
            time_limit=10,
            algorithm_interface=alg.interfaces.first(),
        )
        j.inputs.set(civs)

        jobs = Job.objects.get_jobs_with_same_inputs(
            inputs=data,
            algorithm_image=alg.active_image,
            algorithm_model=alg.active_model,
        )
        assert len(jobs) == 0

    def test_job_with_same_model_different_image(
        self, algorithm_with_image_and_model_and_two_inputs
    ):
        alg = algorithm_with_image_and_model_and_two_inputs.algorithm
        civs = algorithm_with_image_and_model_and_two_inputs.civs
        data = self.get_civ_data(civs=civs)

        j = AlgorithmJobFactory(
            algorithm_image=AlgorithmImageFactory(),
            algorithm_model=alg.active_model,
            time_limit=10,
            algorithm_interface=alg.interfaces.first(),
        )
        j.inputs.set(civs)
        jobs = Job.objects.get_jobs_with_same_inputs(
            inputs=data,
            algorithm_image=alg.active_image,
            algorithm_model=alg.active_model,
        )
        assert len(jobs) == 0

    def test_job_with_same_model_and_image(
        self, algorithm_with_image_and_model_and_two_inputs
    ):
        alg = algorithm_with_image_and_model_and_two_inputs.algorithm
        civs = algorithm_with_image_and_model_and_two_inputs.civs
        data = self.get_civ_data(civs=civs)

        j = AlgorithmJobFactory(
            algorithm_model=alg.active_model,
            algorithm_image=alg.active_image,
            time_limit=10,
            algorithm_interface=alg.interfaces.first(),
        )
        j.inputs.set(civs)
        jobs = Job.objects.get_jobs_with_same_inputs(
            inputs=data,
            algorithm_image=alg.active_image,
            algorithm_model=alg.active_model,
        )
        assert len(jobs) == 1
        assert j in jobs

    def test_job_with_different_image_and_model(
        self, algorithm_with_image_and_model_and_two_inputs
    ):
        alg = algorithm_with_image_and_model_and_two_inputs.algorithm
        civs = algorithm_with_image_and_model_and_two_inputs.civs
        data = self.get_civ_data(civs=civs)

        j = AlgorithmJobFactory(
            algorithm_model=AlgorithmModelFactory(),
            algorithm_image=AlgorithmImageFactory(),
            time_limit=10,
            algorithm_interface=alg.interfaces.first(),
        )
        j.inputs.set(civs)
        jobs = Job.objects.get_jobs_with_same_inputs(
            inputs=data,
            algorithm_image=alg.active_image,
            algorithm_model=alg.active_model,
        )
        assert len(jobs) == 0

    def test_job_with_same_image_no_model_provided(
        self, algorithm_with_image_and_model_and_two_inputs
    ):
        alg = algorithm_with_image_and_model_and_two_inputs.algorithm
        civs = algorithm_with_image_and_model_and_two_inputs.civs
        data = self.get_civ_data(civs=civs)

        j = AlgorithmJobFactory(
            algorithm_model=alg.active_model,
            algorithm_image=alg.active_image,
            time_limit=10,
            algorithm_interface=alg.interfaces.first(),
        )
        j.inputs.set(civs)
        jobs = Job.objects.get_jobs_with_same_inputs(
            inputs=data,
            algorithm_image=alg.active_image,
            algorithm_model=None,
        )
        assert len(jobs) == 0

    def test_job_with_same_image_and_without_model(
        self, algorithm_with_image_and_model_and_two_inputs
    ):
        alg = algorithm_with_image_and_model_and_two_inputs.algorithm
        civs = algorithm_with_image_and_model_and_two_inputs.civs
        data = self.get_civ_data(civs=civs)

        j = AlgorithmJobFactory(
            algorithm_image=alg.active_image,
            time_limit=10,
            algorithm_interface=alg.interfaces.first(),
        )
        j.inputs.set(civs)
        jobs = Job.objects.get_jobs_with_same_inputs(
            inputs=data,
            algorithm_image=alg.active_image,
            algorithm_model=None,
        )
        assert j in jobs
        assert len(jobs) == 1

    def test_job_with_different_input(
        self, algorithm_with_image_and_model_and_two_inputs
    ):
        alg = algorithm_with_image_and_model_and_two_inputs.algorithm
        civs = algorithm_with_image_and_model_and_two_inputs.civs
        data = self.get_civ_data(civs=civs)

        j = AlgorithmJobFactory(
            algorithm_image=alg.active_image,
            time_limit=10,
            algorithm_interface=alg.interfaces.first(),
        )
        j.inputs.set(
            [
                ComponentInterfaceValueFactory(),
                ComponentInterfaceValueFactory(),
            ]
        )
        jobs = Job.objects.get_jobs_with_same_inputs(
            inputs=data,
            algorithm_image=alg.active_image,
            algorithm_model=None,
        )
        assert len(jobs) == 0

    def test_job_with_partially_overlapping_input(
        self, algorithm_with_image_and_model_and_two_inputs
    ):
        alg = algorithm_with_image_and_model_and_two_inputs.algorithm
        civs = algorithm_with_image_and_model_and_two_inputs.civs
        data = self.get_civ_data(civs=civs)

        j = AlgorithmJobFactory(
            algorithm_image=alg.active_image,
            time_limit=10,
            algorithm_interface=alg.interfaces.first(),
        )
        j.inputs.set(
            [
                civs[0],
                ComponentInterfaceValueFactory(),
            ]
        )
        j2 = AlgorithmJobFactory(
            algorithm_image=alg.active_image,
            time_limit=10,
            algorithm_interface=alg.interfaces.first(),
        )
        j2.inputs.set(
            [
                civs[0],
                civs[1],
                ComponentInterfaceValueFactory(),
            ]
        )
        jobs = Job.objects.get_jobs_with_same_inputs(
            inputs=data,
            algorithm_image=alg.active_image,
            algorithm_model=None,
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
    settings.ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER = 1000

    minimum_credits_per_job = 300

    u = UserFactory()
    ai = AlgorithmImageFactory(
        algorithm__minimum_credits_per_job=minimum_credits_per_job,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )

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
def test_non_editor_remaining_jobs(settings):
    settings.ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER = 1000

    minimum_credits_per_job = 300

    u = UserFactory()
    ai = AlgorithmImageFactory(
        algorithm__minimum_credits_per_job=minimum_credits_per_job,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )

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
    interface = AlgorithmInterfaceFactory(
        inputs=[ci1, ci2, ci3], outputs=[ComponentInterfaceFactory()]
    )
    alg.interfaces.add(interface)
    job = AlgorithmJobFactory(
        algorithm_image__algorithm=alg,
        time_limit=10,
        algorithm_interface=alg.interfaces.first(),
    )
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

    job.inputs.set([civ_with_value_1, civ_with_value_2])
    del job.inputs_complete
    assert not job.inputs_complete

    job.inputs.set([civ_with_value_1, civ_with_value_2, civ_with_value_3])
    del job.inputs_complete
    assert job.inputs_complete


@pytest.mark.django_db
@pytest.mark.parametrize(
    "requires_gpu_type,requires_memory_gb,time_limit,expected_credits",
    (
        (GPUTypeChoices.NO_GPU, 4, 60, 20),
        (GPUTypeChoices.NO_GPU, 32, 3600, 40),
        (GPUTypeChoices.NO_GPU, 32, 1800, 20),
        (GPUTypeChoices.NO_GPU, 16, 3600, 20),
        (GPUTypeChoices.V100, 32, 3600, 460),
        (GPUTypeChoices.T4, 32, 3600, 120),
        (GPUTypeChoices.T4, 32, 1800, 60),
        (GPUTypeChoices.T4, 16, 3600, 90),
    ),
)
def test_credits_consumed(
    settings,
    requires_gpu_type,
    requires_memory_gb,
    time_limit,
    expected_credits,
):
    settings.COMPONENTS_DEFAULT_BACKEND = "grandchallenge.components.backends.amazon_sagemaker_training.AmazonSageMakerTrainingExecutor"

    ai = AlgorithmImageFactory(
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
        algorithm__time_limit=time_limit,
        algorithm__job_requires_gpu_type=requires_gpu_type,
        algorithm__job_requires_memory_gb=requires_memory_gb,
    )

    job = AlgorithmJobFactory(
        algorithm_image=ai,
        requires_gpu_type=ai.algorithm.job_requires_gpu_type,
        requires_memory_gb=ai.algorithm.job_requires_memory_gb,
        time_limit=ai.algorithm.time_limit,
    )

    assert job.credits_consumed == expected_credits
    assert job.algorithm_image.algorithm.credits_per_job == expected_credits


@pytest.mark.django_db
@pytest.mark.parametrize(
    "min_credits,time_limit,expected_credits",
    (
        # Set below the system minimum
        (10, 1, 20),
        # Above the system minimum but job costs more
        (50, 3600, 110),
        # Ensure this minimum
        (500, 3600, 500),
    ),
)
def test_min_credits_per_job(min_credits, time_limit, expected_credits):
    ai = AlgorithmImageFactory(
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
        algorithm__time_limit=time_limit,
        algorithm__minimum_credits_per_job=min_credits,
    )

    job = AlgorithmJobFactory(
        algorithm_image=ai,
        requires_gpu_type=ai.algorithm.job_requires_gpu_type,
        requires_memory_gb=ai.algorithm.job_requires_memory_gb,
        time_limit=ai.algorithm.time_limit,
    )

    assert job.credits_consumed == expected_credits
    assert job.algorithm_image.algorithm.credits_per_job == expected_credits


@pytest.mark.django_db
def test_requires_gpu_unchangable():
    job = AlgorithmJobFactory(
        time_limit=60,
    )

    job.requires_gpu_type = GPUTypeChoices.T4

    with pytest.raises(ValueError) as error:
        job.save()

    assert "requires_gpu_type cannot be changed" in str(error)


@pytest.mark.django_db
def test_requires_memory_unchangable():
    job = AlgorithmJobFactory(
        time_limit=60,
    )

    job.requires_memory_gb = 500

    with pytest.raises(ValueError) as error:
        job.save()

    assert "requires_memory_gb cannot be changed" in str(error)


@pytest.mark.django_db
def test_time_limit_unchangable():
    job = AlgorithmJobFactory(
        time_limit=60,
    )

    job.time_limit = 500

    with pytest.raises(ValueError) as error:
        job.save()

    assert "time_limit cannot be changed" in str(error)


@pytest.mark.django_db
class TestAlgorithmUserCreditValidation:
    def test_anonymous_user_validation(self):
        """Test that credits cannot be assigned to anonymous users"""
        anonymous_user = get_user_model().objects.get(
            username=settings.ANONYMOUS_USER_NAME
        )
        algorithm = AlgorithmFactory()

        with pytest.raises(ValidationError) as error:
            AlgorithmUserCredit.objects.create(
                user=anonymous_user,
                algorithm=algorithm,
                credits=100,
                valid_from=now().date(),
                valid_until=now().date() + timedelta(days=30),
                comment="Test credit",
            )

        assert "The anonymous user cannot be assigned credits" in str(
            error.value
        )

    def test_date_validation(self):
        """Test that valid_until cannot be before valid_from"""
        today = now().date()
        yesterday = today - timedelta(days=1)
        algorithm = AlgorithmFactory()

        with pytest.raises(ValidationError) as error:
            AlgorithmUserCredit.objects.create(
                user=UserFactory(),
                algorithm=algorithm,
                credits=100,
                valid_from=today,
                valid_until=yesterday,
                comment="Test credit",
            )

        assert "This must be less than or equal to Valid Until" in str(
            error.value
        )
        assert "This must be greater than or equal to Valid From" in str(
            error.value
        )

    def test_missing_dates(self):
        """Test that both dates must be set"""
        algorithm = AlgorithmFactory()

        with pytest.raises(ValidationError) as error:
            AlgorithmUserCredit.objects.create(
                user=UserFactory(),
                algorithm=algorithm,
                credits=100,
                valid_from=None,
                valid_until=None,
                comment="Test credit",
            )

        assert "The validity period must be set" in str(error.value)

    def test_valid_credit_creation(self):
        """Test that valid credits can be created"""
        today = now().date()
        next_month = today + timedelta(days=30)
        user = UserFactory()
        algorithm = AlgorithmFactory()

        credit = AlgorithmUserCredit.objects.create(
            user=user,
            algorithm=algorithm,
            credits=100,
            valid_from=today,
            valid_until=next_month,
            comment="Test credit",
        )

        assert credit.user == user
        assert credit.algorithm == algorithm
        assert credit.credits == 100
        assert credit.valid_from == today
        assert credit.valid_until == next_month
        assert credit.comment == "Test credit"


@pytest.mark.django_db
class TestAlgorithmImageCredits:
    def test_no_credits(self, settings):
        settings.ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER = 1000

        user = UserFactory()
        algorithm = AlgorithmFactory(minimum_credits_per_job=500)
        algorithm_image = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            algorithm=algorithm,
        )

        n_jobs = settings.ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER // 500

        assert (
            algorithm_image.get_remaining_non_complimentary_jobs(user=user)
            == n_jobs
        )

        # Create some jobs that use up all credits
        for _ in range(n_jobs):
            job = AlgorithmJobFactory(
                creator=user,
                algorithm_image=algorithm_image,
                is_complimentary=False,
                time_limit=3600,
            )
            job.credits_consumed = 500
            job.save()

        # User should now have no credits left
        assert (
            algorithm_image.get_remaining_non_complimentary_jobs(user=user)
            == 0
        )

    def test_credits_for_other_algorithm(self, settings):
        settings.ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER = 1000

        user = UserFactory()
        algorithm1 = AlgorithmFactory(minimum_credits_per_job=200)
        algorithm2 = AlgorithmFactory(minimum_credits_per_job=200)

        algorithm_image1 = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            algorithm=algorithm1,
        )
        algorithm_image2 = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            algorithm=algorithm2,
        )

        # Give user credits for algorithm1
        AlgorithmUserCreditFactory(
            user=user,
            algorithm=algorithm1,
            credits=10000,
            valid_from=now().date(),
            valid_until=now().date() + timedelta(days=30),
            comment="test",
        )

        # User should have 50 jobs for algorithm1 (10000 credits / 200 credits per job)
        assert (
            algorithm_image1.get_remaining_non_complimentary_jobs(user=user)
            == 50
        )

        # For algorithm2, user should have general credits
        assert (
            algorithm_image2.get_remaining_non_complimentary_jobs(user=user)
            == 5
        )

    def test_expired_credits(self, settings):
        settings.ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER = 1000

        # Test that expired credits are not counted
        user = UserFactory()
        algorithm = AlgorithmFactory(minimum_credits_per_job=200)
        algorithm_image = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            algorithm=algorithm,
        )

        # Create expired credits
        AlgorithmUserCreditFactory(
            user=user,
            algorithm=algorithm,
            credits=10000,
            valid_from=now().date() - timedelta(days=60),
            valid_until=now().date() - timedelta(days=30),
            comment="test",
        )

        # User should only have general credits since the specific credits are expired
        assert (
            algorithm_image.get_remaining_non_complimentary_jobs(user=user)
            == 5
        )

    def test_future_credits(self, settings):
        settings.ALGORITHMS_GENERAL_CREDITS_PER_MONTH_PER_USER = 1000

        # Test that future credits are not counted
        user = UserFactory()
        algorithm = AlgorithmFactory(minimum_credits_per_job=200)
        algorithm_image = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            algorithm=algorithm,
        )

        # Create future credits
        AlgorithmUserCreditFactory(
            user=user,
            algorithm=algorithm,
            credits=10000,
            valid_from=now().date() + timedelta(days=30),
            valid_until=now().date() + timedelta(days=60),
            comment="test",
        )

        # User should only have general credits since the specific credits are in the future
        assert (
            algorithm_image.get_remaining_non_complimentary_jobs(user=user)
            == 5
        )

    def test_active_credits_with_spent_credits(self):

        user = UserFactory()
        algorithm = AlgorithmFactory(minimum_credits_per_job=200)
        algorithm_image = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
            algorithm=algorithm,
        )

        AlgorithmUserCreditFactory(
            user=user,
            algorithm=algorithm,
            credits=2000,
            valid_from=now().date(),
            valid_until=now().date() + timedelta(days=30),
            comment="test",
        )

        for _ in range(5):
            job = AlgorithmJobFactory(
                creator=user,
                algorithm_image=algorithm_image,
                is_complimentary=False,
                time_limit=3600,
            )
            job.credits_consumed = 200
            job.save()

        assert (
            algorithm_image.get_remaining_non_complimentary_jobs(user=user)
            == 5
        )


@pytest.mark.django_db
def test_algorithm_interface_cannot_be_deleted():
    interface, _, _ = AlgorithmInterfaceFactory.create_batch(3)

    with pytest.raises(ValidationError):
        interface.delete()

    with pytest.raises(NotImplementedError):
        AlgorithmInterface.objects.delete()


@pytest.mark.django_db
def test_algorithmalgorithminterface_unique_constraints():
    interface1, interface2 = AlgorithmInterfaceFactory.create_batch(2)
    algorithm = AlgorithmFactory()

    AlgorithmAlgorithmInterface.objects.create(
        interface=interface1, algorithm=algorithm
    )

    # cannot add a second time the same interface for the same algorithm
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AlgorithmAlgorithmInterface.objects.create(
                interface=interface1, algorithm=algorithm
            )


@pytest.mark.parametrize(
    "inputs, outputs, expected_output",
    (
        ([1], [2], 1),
        ([1, 2], [3, 4], 2),
        ([3, 4, 5], [6], 3),
        ([1], [3, 4, 6], 4),
        ([5, 6], [2], 5),
        ([1], [3], None),
        ([1], [3, 4], None),
        ([2], [6], None),
        ([2], [1], None),
        ([3, 4, 5], [1], None),
        ([1], [3, 4], None),
        ([1, 3], [4], None),
    ),
)
@pytest.mark.django_db
def test_get_existing_interface_for_inputs_and_outputs(
    inputs, outputs, expected_output
):
    io1, io2, io3, io4, io5, io6 = AlgorithmInterfaceFactory.create_batch(6)
    ci1, ci2, ci3, ci4, ci5, ci6 = ComponentInterfaceFactory.create_batch(6)

    interfaces = [io1, io2, io3, io4, io5, io6]
    cis = [ci1, ci2, ci3, ci4, ci5, ci6]

    io1.inputs.set([ci1])
    io2.inputs.set([ci1, ci2])
    io3.inputs.set([ci3, ci4, ci5])
    io4.inputs.set([ci1])
    io5.inputs.set([ci5, ci6])
    io6.inputs.set([ci1, ci2])

    io1.outputs.set([ci2])
    io2.outputs.set([ci3, ci4])
    io3.outputs.set([ci6])
    io4.outputs.set([ci3, ci4, ci6])
    io5.outputs.set([ci2])
    io6.outputs.set([ci4])

    inputs = [cis[i - 1] for i in inputs]
    outputs = [cis[i - 1] for i in outputs]

    existing_interface = get_existing_interface_for_inputs_and_outputs(
        inputs=inputs, outputs=outputs
    )

    if expected_output:
        assert existing_interface == interfaces[expected_output - 1]
    else:
        assert not existing_interface


@pytest.mark.django_db
def test_algorithminterface_create():
    inputs = [ComponentInterfaceFactory(), ComponentInterfaceFactory()]
    outputs = [ComponentInterfaceFactory(), ComponentInterfaceFactory()]

    with pytest.raises(TypeError) as e:
        AlgorithmInterface.objects.create()

    assert (
        "AlgorithmInterfaceManager.create() missing 2 required keyword-only arguments: 'inputs' and 'outputs'"
        in str(e)
    )

    io = AlgorithmInterface.objects.create(inputs=inputs, outputs=outputs)
    assert list(io.inputs.all()) == inputs
    assert list(io.outputs.all()) == outputs
