import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from guardian.shortcuts import (
    assign_perm,
    get_group_perms,
    get_perms,
    get_users_with_perms,
)

from grandchallenge.algorithms.models import Job
from grandchallenge.algorithms.serializers import JobPostSerializer
from grandchallenge.components.models import ComponentInterface, InterfaceKind
from grandchallenge.evaluation.models import Evaluation
from grandchallenge.evaluation.tasks import (
    create_algorithm_jobs_for_evaluation,
)
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmInterfaceFactory,
    AlgorithmJobFactory,
)
from tests.algorithms_tests.utils import TwoAlgorithms
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.conftest import get_interface_form_data
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
from tests.verification_tests.factories import VerificationFactory


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
        algorithm_image__algorithm=alg_set.alg1,
        creator=j1_creator,
        time_limit=alg_set.alg1.time_limit,
    )
    alg2_job = AlgorithmJobFactory(
        algorithm_image__algorithm=alg_set.alg2,
        creator=j2_creator,
        time_limit=alg_set.alg2.time_limit,
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
    algorithm_job = AlgorithmJobFactory(time_limit=60, public=False)

    assert "view_job" not in get_perms(g_reg, algorithm_job)
    assert "view_job" not in get_perms(g_reg_anon, algorithm_job)

    algorithm_job.public = True
    algorithm_job.save()

    assert "view_job" not in get_perms(g_reg, algorithm_job)
    assert "view_job" in get_perms(g_reg_anon, algorithm_job)


@pytest.mark.django_db
def test_unpublic_job_group_permissions():
    g_reg_anon = Group.objects.get(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )
    g_reg = Group.objects.get(name=settings.REGISTERED_USERS_GROUP_NAME)
    algorithm_job = AlgorithmJobFactory(time_limit=60, public=True)

    assert "view_job" not in get_perms(g_reg, algorithm_job)
    assert "view_job" in get_perms(g_reg_anon, algorithm_job)

    algorithm_job.public = False
    algorithm_job.save()

    assert "view_job" not in get_perms(g_reg, algorithm_job)
    assert "view_job" not in get_perms(g_reg_anon, algorithm_job)


@pytest.mark.django_db
class TestJobPermissions:
    """The permissions for jobs will depend on their creation"""

    @staticmethod
    def _validate_created_job_perms(*, algorithm_image, job, user):
        # Editors should be able to view the logs
        # and viewers should be able to view the job
        assert get_groups_with_set_perms(job) == {
            algorithm_image.algorithm.editors_group: {"view_logs"},
            job.viewers: {"view_job"},
        }
        # The Session Creator should be able to change the job
        # and view the logs
        assert get_users_with_set_perms(
            job, attach_perms=True, with_group_users=False
        ) == {user: {"change_job"}}
        # The only member of the viewers group should be the creator
        assert {*job.viewers.user_set.all()} == {user}

    def test_job_permissions_from_template(self, client):
        algorithm_image = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )

        user = UserFactory()
        editor = UserFactory()
        VerificationFactory(user=user, is_verified=True)

        algorithm_image.algorithm.add_user(user)
        algorithm_image.algorithm.add_editor(editor)
        ci = ComponentInterfaceFactory(
            kind=InterfaceKind.InterfaceKindChoices.ANY,
            store_in_database=True,
        )
        interface = AlgorithmInterfaceFactory(
            inputs=[ci], outputs=[ComponentInterfaceFactory()]
        )
        algorithm_image.algorithm.interfaces.add(interface)

        response = get_view_for_user(
            viewname="algorithms:job-create",
            client=client,
            method=client.post,
            reverse_kwargs={
                "slug": algorithm_image.algorithm.slug,
                "interface_pk": algorithm_image.algorithm.interfaces.first().pk,
            },
            user=user,
            follow=True,
            data={
                **get_interface_form_data(
                    interface_slug=ci.slug, data='{"Foo": "bar"}'
                )
            },
        )
        assert response.status_code == 200

        job = Job.objects.get()

        self._validate_created_job_perms(
            algorithm_image=algorithm_image, job=job, user=user
        )

    def test_job_permissions_from_api(self, rf):
        # setup
        user = UserFactory()
        algorithm_image = AlgorithmImageFactory(
            is_manifest_valid=True,
            is_in_registry=True,
            is_desired_version=True,
        )
        ci = ComponentInterfaceFactory(
            kind=ComponentInterface.Kind.STRING,
            title="TestInterface 1",
            default_value="default",
        )

        interface = AlgorithmInterfaceFactory(inputs=[ci])
        algorithm_image.algorithm.interfaces.add(interface)
        algorithm_image.algorithm.add_user(user)
        algorithm_image.algorithm.add_editor(UserFactory())

        job = {
            "algorithm": algorithm_image.algorithm.api_url,
            "inputs": [{"interface": ci.slug, "value": "foo"}],
        }

        # test
        request = rf.get("/foo")
        request.user = user
        serializer = JobPostSerializer(data=job, context={"request": request})

        # verify
        assert serializer.is_valid()
        serializer.create(serializer.validated_data)
        job = Job.objects.get()
        assert job.creator == user
        assert len(job.inputs.all()) == 1

        self._validate_created_job_perms(
            algorithm_image=algorithm_image, job=job, user=user
        )

    def test_job_permissions_for_normal_phase(
        self, django_capture_on_commit_callbacks
    ):
        ai = AlgorithmImageFactory()
        archive = ArchiveFactory()
        evaluation = EvaluationFactory(
            submission__phase__archive=archive,
            submission__algorithm_image=ai,
            time_limit=ai.algorithm.time_limit,
            status=Evaluation.EXECUTING_PREREQUISITES,
        )

        # The default should be not to share the jobs
        assert (
            evaluation.submission.phase.give_algorithm_editors_job_view_permissions
            is False
        )

        # Fake an image upload via a session
        u = UserFactory()
        s = UploadSessionFactory(creator=u)
        im = ImageFactory()
        s.image_set.set([im])

        ci = ComponentInterface.objects.get(slug="generic-medical-image")
        interface = AlgorithmInterfaceFactory(inputs=[ci])
        ai.algorithm.interfaces.add(interface)
        civ = ComponentInterfaceValueFactory(image=im, interface=ci)

        archive_item = ArchiveItemFactory(archive=archive)
        with django_capture_on_commit_callbacks(execute=True):
            archive_item.values.add(civ)

        create_algorithm_jobs_for_evaluation(
            evaluation_pk=evaluation.pk, first_run=False
        )

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
        }
        # No-one should be able to change the job
        assert (
            get_users_with_perms(
                job, attach_perms=True, with_group_users=False
            )
            == {}
        )
        # The viewers group should not exist for system jobs
        assert job.viewers is None

    def test_job_permissions_for_debug_phase(
        self, django_capture_on_commit_callbacks
    ):
        ai = AlgorithmImageFactory()
        archive = ArchiveFactory()
        evaluation = EvaluationFactory(
            submission__phase__archive=archive,
            submission__algorithm_image=ai,
            time_limit=ai.algorithm.time_limit,
            status=Evaluation.EXECUTING_PREREQUISITES,
        )

        evaluation.submission.phase.give_algorithm_editors_job_view_permissions = (
            True
        )
        evaluation.submission.phase.save()

        # Fake an image upload via a session
        u = UserFactory()
        s = UploadSessionFactory(creator=u)
        im = ImageFactory()
        s.image_set.set([im])

        ci = ComponentInterface.objects.get(slug="generic-medical-image")
        civ = ComponentInterfaceValueFactory(image=im, interface=ci)
        archive_item = ArchiveItemFactory(archive=archive)
        with django_capture_on_commit_callbacks(execute=True):
            archive_item.values.add(civ)

        interface = AlgorithmInterfaceFactory(inputs=[ci])
        ai.algorithm.interfaces.add(interface)

        create_algorithm_jobs_for_evaluation(
            evaluation_pk=evaluation.pk, first_run=False
        )

        job = Job.objects.get()

        # Only the challenge admins and job viewers should be able to view the
        # job and logs.
        # In this case the algorithm editor can see the jobs as the challenge
        # admins have opted in to give_algorithm_editors_job_view_permissions
        assert get_groups_with_set_perms(job) == {
            evaluation.submission.phase.challenge.admins_group: {
                "view_job",
                "view_logs",
            },
            ai.algorithm.editors_group: {
                "view_job",
                "view_logs",
            },
        }
        # No-one should be able to change the job
        assert (
            get_users_with_perms(
                job, attach_perms=True, with_group_users=False
            )
            == {}
        )
        # The viewers group should not exist for system jobs
        assert job.viewers is None
