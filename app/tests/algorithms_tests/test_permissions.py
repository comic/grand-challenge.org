import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase
from django_capture_on_commit_callbacks import capture_on_commit_callbacks
from guardian.shortcuts import (
    assign_perm,
    get_group_perms,
    get_perms,
    get_users_with_perms,
)

from grandchallenge.algorithms.models import Job
from grandchallenge.algorithms.tasks import (
    create_algorithm_jobs_for_archive,
    create_algorithm_jobs_for_session,
)
from grandchallenge.evaluation.tasks import (
    create_algorithm_jobs_for_evaluation,
)
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.algorithms_tests.utils import TwoAlgorithms
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import ComponentInterfaceValueFactory
from tests.evaluation_tests.factories import EvaluationFactory
from tests.evaluation_tests.test_permissions import (
    get_groups_with_set_perms,
    get_users_with_set_perms,
)
from tests.factories import (
    ImageFactory,
    UploadSessionFactory,
    UserFactory,
    WorkstationFactory,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_algorithm_creators_group_has_perm(settings):
    creators_group = Group.objects.get(
        name=settings.ALGORITHMS_CREATORS_GROUP_NAME
    )
    assert creators_group.permissions.filter(codename="add_algorithm").exists()


@pytest.mark.django_db
def test_algorithm_groups_permissions_are_assigned():
    alg = AlgorithmFactory()

    editors_perms = get_group_perms(alg.editors_group, alg)
    assert "view_algorithm" in editors_perms
    assert "change_algorithm" in editors_perms
    assert "execute_algorithm" in editors_perms

    users_perms = get_group_perms(alg.users_group, alg)
    assert "view_algorithm" in users_perms
    assert "change_algorithm" not in users_perms
    assert "execute_algorithm" in users_perms


@pytest.mark.django_db
def test_algorithm_image_group_permissions_are_assigned():
    ai = AlgorithmImageFactory()

    perms = get_group_perms(ai.algorithm.editors_group, ai)
    assert "view_algorithmimage" in perms
    assert "change_algorithmimage" in perms


@pytest.mark.django_db
def test_api_algorithm_list_permissions(client):
    alg_set = TwoAlgorithms()

    tests = (
        (None, 200, []),
        (alg_set.creator, 200, []),
        (alg_set.editor1, 200, [alg_set.alg1.pk]),
        (alg_set.user1, 200, [alg_set.alg1.pk]),
        (alg_set.editor2, 200, [alg_set.alg2.pk]),
        (alg_set.user2, 200, [alg_set.alg2.pk]),
        (alg_set.u, 200, []),
    )

    for test in tests:
        response = get_view_for_user(
            viewname="api:algorithm-list",
            client=client,
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == test[1]

        assert response.json()["count"] == len(test[2])

        pks = {obj["pk"] for obj in response.json()["results"]}
        assert {str(pk) for pk in test[2]} == pks


@pytest.mark.django_db
def test_api_algorithm_image_list_permissions(client):
    alg_set = TwoAlgorithms()

    alg1_image_pk = AlgorithmImageFactory(algorithm=alg_set.alg1).pk
    alg2_image_pk = AlgorithmImageFactory(algorithm=alg_set.alg2).pk

    tests = (
        (None, 200, []),
        (alg_set.creator, 200, []),
        (alg_set.editor1, 200, [alg1_image_pk]),
        (alg_set.user1, 200, []),
        (alg_set.editor2, 200, [alg2_image_pk]),
        (alg_set.user2, 200, []),
        (alg_set.u, 200, []),
    )

    for test in tests:
        response = get_view_for_user(
            viewname="api:algorithms-image-list",
            client=client,
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == test[1]

        assert response.json()["count"] == len(test[2])

        pks = {obj["pk"] for obj in response.json()["results"]}
        assert {str(pk) for pk in test[2]} == pks


@pytest.mark.django_db
def test_api_job_list_permissions(client):
    alg_set = TwoAlgorithms()

    j1_creator, j2_creator = UserFactory(), UserFactory()

    alg1_job = AlgorithmJobFactory(
        algorithm_image__algorithm=alg_set.alg1, creator=j1_creator
    )
    alg2_job = AlgorithmJobFactory(
        algorithm_image__algorithm=alg_set.alg2, creator=j2_creator
    )

    alg1_job.viewer_groups.add(alg_set.alg1.editors_group)
    alg2_job.viewer_groups.add(alg_set.alg2.editors_group)

    tests = (
        (None, 200, []),
        (alg_set.creator, 200, []),
        (alg_set.editor1, 200, [alg1_job]),
        (alg_set.user1, 200, []),
        (j1_creator, 200, [alg1_job]),
        (alg_set.editor2, 200, [alg2_job]),
        (alg_set.user2, 200, []),
        (j2_creator, 200, [alg2_job]),
        (alg_set.u, 200, []),
    )

    for test in tests:
        response = get_view_for_user(
            viewname="api:algorithms-job-list",
            client=client,
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == test[1]

        assert response.json()["count"] == len(test[2])

        job_pks = {obj["pk"] for obj in response.json()["results"]}
        assert job_pks == {str(j.pk) for j in test[2]}

        # Ensure that the images are downloadable
        response = get_view_for_user(
            viewname="api:image-list",
            client=client,
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == 200

        image_pks = {obj["pk"] for obj in response.json()["results"]}
        assert image_pks == {
            str(i.image.pk) for j in test[2] for i in j.inputs.all()
        }


@pytest.mark.django_db
@pytest.mark.parametrize("group", ["user", "editor"])
def test_workstation_changes(client, group):
    # Ensure that read permissions are kept up to date if the workstation
    # changes
    ws1, ws2 = WorkstationFactory(), WorkstationFactory()
    user = UserFactory()

    alg = AlgorithmFactory(workstation=ws1)

    assert "view_workstation" not in get_perms(user, ws1)
    assert "view_workstation" not in get_perms(user, ws2)

    getattr(alg, f"add_{group}")(user=user)

    assert "view_workstation" in get_perms(user, ws1)
    assert "view_workstation" not in get_perms(user, ws2)

    alg.workstation = ws2
    alg.save()

    assert "view_workstation" not in get_perms(user, ws1)
    assert "view_workstation" in get_perms(user, ws2)

    # Test permission cleanup
    assign_perm("view_workstation", getattr(alg, f"{group}s_group"), ws1)

    assert "view_workstation" in get_perms(user, ws1)
    assert "view_workstation" in get_perms(user, ws2)

    alg.save()

    assert "view_workstation" not in get_perms(user, ws1)
    assert "view_workstation" in get_perms(user, ws2)


@pytest.mark.django_db
def test_visible_to_public_group_permissions():
    g_reg_anon = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )
    algorithm = AlgorithmFactory()

    assert "view_algorithm" not in get_perms(g_reg_anon, algorithm)

    algorithm.public = True
    algorithm.save()

    assert "view_algorithm" in get_perms(g_reg_anon, algorithm)

    algorithm.public = False
    algorithm.save()

    assert "view_algorithm" not in get_perms(g_reg_anon, algorithm)


@pytest.mark.django_db
def test_public_job_group_permissions():
    g_reg_anon = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )
    g_reg = Group.objects.get(name=settings.REGISTERED_USERS_GROUP_NAME)
    algorithm_job = AlgorithmJobFactory()

    assert "view_job" not in get_perms(g_reg, algorithm_job)
    assert "view_job" not in get_perms(g_reg_anon, algorithm_job)

    algorithm_job.public = True
    algorithm_job.save()

    assert "view_job" not in get_perms(g_reg, algorithm_job)
    assert "view_job" in get_perms(g_reg_anon, algorithm_job)

    algorithm_job.public = False
    algorithm_job.save()

    assert "view_job" not in get_perms(g_reg, algorithm_job)
    assert "view_job" not in get_perms(g_reg_anon, algorithm_job)


class TestJobPermissions(TestCase):
    """The permissions for jobs will depend on their creation"""

    def test_job_permissions_for_session(self):
        ai = AlgorithmImageFactory(ready=True)

        u = UserFactory()
        s = UploadSessionFactory(creator=u)
        im = ImageFactory()
        s.image_set.set([im])

        create_algorithm_jobs_for_session(
            upload_session_pk=s.pk, algorithm_image_pk=ai.pk
        )

        job = Job.objects.get()

        # Editors and viewers should be able to view the job
        assert get_groups_with_set_perms(job) == {
            ai.algorithm.editors_group: {"view_job", "view_logs"},
            job.viewers: {"view_job"},
        }
        # The Session Creator should be able to change the job
        # and view the logs
        assert get_users_with_set_perms(
            job, attach_perms=True, with_group_users=False
        ) == {u: {"change_job"}}
        # The only member of the viewers group should be the creator
        assert {*job.viewers.user_set.all()} == {u}

    def test_job_permissions_for_archive(self):
        ai = AlgorithmImageFactory(ready=True)
        archive = ArchiveFactory()

        # Fake an image upload via a session
        u = UserFactory()
        s = UploadSessionFactory(creator=u)
        im = ImageFactory()
        s.image_set.set([im])

        civ = ComponentInterfaceValueFactory(
            image=im, interface=ai.algorithm.inputs.get()
        )
        archive_item = ArchiveItemFactory(archive=archive)
        with capture_on_commit_callbacks(execute=True):
            archive_item.values.add(civ)

        archive.algorithms.set([ai.algorithm])

        create_algorithm_jobs_for_archive(archive_pks=[archive.pk])

        job = Job.objects.get()

        # The archive editors, users and uploaders and job
        # viewers should be able to view the job.
        # NOTE: NOT THE ALGORITHM EDITORS, if they need
        # access the job can be shared with them.
        assert get_groups_with_set_perms(job) == {
            archive.editors_group: {"view_job"},
            archive.users_group: {"view_job"},
            archive.uploaders_group: {"view_job"},
            job.viewers: {"view_job"},
        }
        # No-one should be able to change the job
        assert (
            get_users_with_perms(
                job, attach_perms=True, with_group_users=False
            )
            == {}
        )
        # No-one should be in the viewers group
        assert {*job.viewers.user_set.all()} == set()

    def test_job_permissions_for_challenge(self):
        ai = AlgorithmImageFactory(ready=True)
        archive = ArchiveFactory()
        evaluation = EvaluationFactory(
            submission__phase__archive=archive, submission__algorithm_image=ai
        )

        # Fake an image upload via a session
        u = UserFactory()
        s = UploadSessionFactory(creator=u)
        im = ImageFactory()
        s.image_set.set([im])

        civ = ComponentInterfaceValueFactory(
            image=im, interface=ai.algorithm.inputs.get()
        )
        archive_item = ArchiveItemFactory(archive=archive)
        with capture_on_commit_callbacks(execute=True):
            archive_item.values.add(civ)

        create_algorithm_jobs_for_evaluation(evaluation_pk=evaluation.pk)

        job = Job.objects.get()

        # Only the challenge admins and job viewers should be able to view the
        # job and logs.
        # NOTE: NOT THE *ALGORITHM* EDITORS, they are the participants
        # to the challenge and should not be able to see the test data
        assert get_groups_with_set_perms(job) == {
            evaluation.submission.phase.challenge.admins_group: {
                "view_job",
                "view_logs",
            },
            job.viewers: {"view_job"},
        }
        # No-one should be able to change the job
        assert (
            get_users_with_perms(
                job, attach_perms=True, with_group_users=False
            )
            == {}
        )
        # No-one should be in the viewers group
        assert {*job.viewers.user_set.all()} == set()
