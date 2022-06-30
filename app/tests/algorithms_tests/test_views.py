import datetime

import pytest
from django.contrib.auth.models import Group
from django.utils import timezone
from django.utils.text import slugify
from guardian.shortcuts import assign_perm, remove_perm

from config import settings
from grandchallenge.algorithms.models import Algorithm, AlgorithmImage, Job
from grandchallenge.subdomains.utils import reverse
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
    AlgorithmPermissionRequestFactory,
)
from tests.archives_tests.factories import ArchiveFactory
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.evaluation_tests.factories import PhaseFactory
from tests.factories import UserFactory, WorkstationConfigFactory
from tests.hanging_protocols_tests.factories import HangingProtocolFactory
from tests.uploads_tests.factories import UserUploadFactory
from tests.utils import get_view_for_user
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
def test_create_link_view(client, settings):
    user = UserFactory()

    response = get_view_for_user(
        viewname="algorithms:list", client=client, user=user
    )
    assert reverse("algorithms:create") not in response.rendered_content

    g = Group.objects.get(name=settings.ALGORITHMS_CREATORS_GROUP_NAME)
    g.user_set.add(user)

    response = get_view_for_user(
        viewname="algorithms:list", client=client, user=user
    )
    assert reverse("algorithms:create") in response.rendered_content


@pytest.mark.django_db
def test_algorithm_list_view(client):
    alg1, alg2 = AlgorithmFactory(), AlgorithmFactory()
    user = UserFactory()

    alg1.add_user(user)
    alg2.add_user(user)

    response = get_view_for_user(
        viewname="algorithms:list", client=client, user=user
    )

    assert alg1.get_absolute_url() in response.rendered_content
    assert alg2.get_absolute_url() in response.rendered_content

    alg1.remove_user(user)

    response = get_view_for_user(
        viewname="algorithms:list", client=client, user=user
    )

    assert alg1.get_absolute_url() not in response.rendered_content
    assert alg2.get_absolute_url() in response.rendered_content


@pytest.mark.django_db
def test_algorithm_list_view_filter(client):
    user = UserFactory()
    alg1, alg2, pubalg = (
        AlgorithmFactory(),
        AlgorithmFactory(),
        AlgorithmFactory(public=True),
    )
    alg1.add_user(user)

    response = get_view_for_user(
        viewname="algorithms:list", client=client, user=user
    )

    assert response.status_code == 200
    assert alg1.get_absolute_url() in response.rendered_content
    assert alg2.get_absolute_url() not in response.rendered_content
    assert pubalg.get_absolute_url() in response.rendered_content


@pytest.mark.django_db
def test_algorithm_image_create_link_view(client):
    alg = AlgorithmFactory()
    expected_url = reverse(
        "algorithms:image-create", kwargs={"slug": alg.slug}
    )
    user = UserFactory()

    alg.add_user(user)

    response = get_view_for_user(
        viewname="algorithms:detail",
        reverse_kwargs={"slug": alg.slug},
        client=client,
        user=user,
    )
    assert response.status_code == 200
    assert expected_url not in response.rendered_content

    alg.add_editor(user)

    response = get_view_for_user(
        viewname="algorithms:detail",
        reverse_kwargs={"slug": alg.slug},
        client=client,
        user=user,
    )
    assert response.status_code == 200
    assert expected_url in response.rendered_content


@pytest.mark.django_db
def test_algorithm_image_create_detail(client):
    user = UserFactory()
    VerificationFactory(user=user, is_verified=True)
    algorithm = AlgorithmFactory()
    algorithm.add_editor(user)

    algorithm_image = UserUploadFactory(
        filename="test_image.tar.gz", creator=user
    )
    algorithm_image.status = algorithm_image.StatusChoices.COMPLETED
    algorithm_image.save()

    response = get_view_for_user(
        client=client,
        viewname="algorithms:image-create",
        reverse_kwargs={"slug": algorithm.slug},
        user=user,
    )
    assert response.status_code == 200

    assert AlgorithmImage.objects.all().count() == 0

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="algorithms:image-create",
        reverse_kwargs={"slug": algorithm.slug},
        user=user,
        data={
            "user_upload": algorithm_image.pk,
            "requires_memory_gb": 24,
            "creator": user.pk,
            "algorithm": algorithm.pk,
        },
    )
    assert response.status_code == 302

    images = AlgorithmImage.objects.all()
    assert len(images) == 1
    assert images[0].algorithm == algorithm
    assert response.url == reverse(
        "algorithms:image-detail",
        kwargs={"slug": algorithm.slug, "pk": images[0].pk},
    )


@pytest.mark.django_db
def test_algorithm_run(client):
    user = UserFactory()
    ai1 = AlgorithmImageFactory(ready=True)
    ai1.algorithm.users_group.user_set.add(user)

    response = get_view_for_user(
        viewname="algorithms:execution-session-create-batch",
        reverse_kwargs={"slug": slugify(ai1.algorithm.slug)},
        client=client,
        user=user,
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_algorithm_permission_request_list(client):
    user = UserFactory()
    editor = UserFactory()

    alg = AlgorithmFactory(public=True)
    alg.add_editor(editor)

    pr = AlgorithmPermissionRequestFactory(algorithm=alg, user=user)

    response = get_view_for_user(
        viewname="algorithms:permission-request-list",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=editor,
        method=client.get,
        follow=True,
    )

    assert response.status_code == 200
    assert pr.user.username in response.rendered_content

    response = get_view_for_user(
        viewname="algorithms:permission-request-list",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=user,
        method=client.get,
        follow=True,
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_algorithm_jobs_list_view(client):
    editor = UserFactory()

    alg = AlgorithmFactory(public=True)
    alg.add_editor(editor)
    im = AlgorithmImageFactory(algorithm=alg)
    for x in range(50):
        created = timezone.now() - datetime.timedelta(days=x + 365)
        job = AlgorithmJobFactory(algorithm_image=im, status=Job.SUCCESS)
        job.created = created
        job.save()
        job.viewer_groups.add(alg.editors_group)

    response = get_view_for_user(
        viewname="algorithms:job-list",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=editor,
        method=client.get,
        follow=True,
    )

    assert response.status_code == 200

    response = get_view_for_user(
        viewname="algorithms:job-list",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=editor,
        method=client.get,
        follow=True,
        data={
            "length": 10,
            "draw": 1,
            "order[0][dir]": "desc",
            "order[0][column]": 0,
        },
        **{"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
    )

    resp = response.json()
    assert resp["recordsTotal"] == 50
    assert len(resp["data"]) == 10

    response = get_view_for_user(
        viewname="algorithms:job-list",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=editor,
        method=client.get,
        follow=True,
        data={
            "length": 50,
            "draw": 1,
            "order[0][dir]": "desc",
            "order[0][column]": 0,
        },
        **{"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
    )

    resp = response.json()
    assert resp["recordsTotal"] == 50
    assert len(resp["data"]) == 50

    response = get_view_for_user(
        viewname="algorithms:job-list",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=editor,
        method=client.get,
        follow=True,
        data={
            "length": 50,
            "draw": 1,
            "order[0][dir]": "asc",
            "order[0][column]": 0,
        },
        **{"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
    )

    resp_new = response.json()
    assert resp_new["recordsTotal"] == 50
    assert resp_new["data"] == resp["data"][::-1]

    response = get_view_for_user(
        viewname="algorithms:job-list",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=editor,
        method=client.get,
        follow=True,
        data={
            "length": 50,
            "draw": 1,
            "search[value]": job.creator.username,
            "order[0][column]": 0,
        },
        **{"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
    )

    resp = response.json()
    assert resp["recordsTotal"] == 50
    assert resp["recordsFiltered"] == 1
    assert len(resp["data"]) == 1


@pytest.mark.django_db
class TestObjectPermissionRequiredViews:
    def test_permission_required_views(self, client):
        ai = AlgorithmImageFactory(ready=True)
        s = RawImageUploadSessionFactory()
        u = UserFactory()
        j = AlgorithmJobFactory(algorithm_image=ai)
        p = AlgorithmPermissionRequestFactory(algorithm=ai.algorithm)

        VerificationFactory(user=u, is_verified=True)

        for view_name, kwargs, permission, obj, redirect in [
            ("create", {}, "algorithms.add_algorithm", None, None),
            (
                "detail",
                {"slug": ai.algorithm.slug},
                "view_algorithm",
                ai.algorithm,
                reverse(
                    "algorithms:permission-request-create",
                    kwargs={"slug": ai.algorithm.slug},
                ),
            ),
            (
                "update",
                {"slug": ai.algorithm.slug},
                "change_algorithm",
                ai.algorithm,
                None,
            ),
            (
                "image-create",
                {"slug": ai.algorithm.slug},
                "change_algorithm",
                ai.algorithm,
                None,
            ),
            (
                "image-detail",
                {"slug": ai.algorithm.slug, "pk": ai.pk},
                "view_algorithmimage",
                ai,
                None,
            ),
            (
                "image-update",
                {"slug": ai.algorithm.slug, "pk": ai.pk},
                "change_algorithmimage",
                ai,
                None,
            ),
            (
                "execution-session-create-batch",
                {"slug": ai.algorithm.slug},
                "execute_algorithm",
                ai.algorithm,
                None,
            ),
            (
                "execution-session-create",
                {"slug": ai.algorithm.slug},
                "execute_algorithm",
                ai.algorithm,
                None,
            ),
            (
                "execution-session-detail",
                {"slug": ai.algorithm.slug, "pk": s.pk},
                "view_rawimageuploadsession",
                s,
                None,
            ),
            (
                "job-experiment-detail",
                {"slug": ai.algorithm.slug, "pk": j.pk},
                "view_job",
                j,
                None,
            ),
            (
                "job-detail",
                {"slug": ai.algorithm.slug, "pk": j.pk},
                "view_job",
                j,
                None,
            ),
            (
                "job-update",
                {"slug": ai.algorithm.slug, "pk": j.pk},
                "change_job",
                j,
                None,
            ),
            (
                "job-viewers-update",
                {"slug": ai.algorithm.slug, "pk": j.pk},
                "change_job",
                j,
                None,
            ),
            (
                "editors-update",
                {"slug": ai.algorithm.slug},
                "change_algorithm",
                ai.algorithm,
                None,
            ),
            (
                "users-update",
                {"slug": ai.algorithm.slug},
                "change_algorithm",
                ai.algorithm,
                None,
            ),
            (
                "permission-request-update",
                {"slug": ai.algorithm.slug, "pk": p.pk},
                "change_algorithm",
                ai.algorithm,
                None,
            ),
            (
                "publish",
                {"slug": ai.algorithm.slug},
                "change_algorithm",
                ai.algorithm,
                None,
            ),
        ]:

            def _get_view():
                return get_view_for_user(
                    client=client,
                    viewname=f"algorithms:{view_name}",
                    reverse_kwargs=kwargs,
                    user=u,
                )

            response = _get_view()
            if redirect is not None:
                assert response.status_code == 302
                assert response.url == redirect
            else:
                assert response.status_code == 403

            assign_perm(permission, u, obj)

            response = _get_view()
            assert response.status_code == 200

            remove_perm(permission, u, obj)

    def test_permission_required_list_views(self, client):
        ai = AlgorithmImageFactory(ready=True)
        u = UserFactory()
        j = AlgorithmJobFactory(algorithm_image=ai)

        for view_name, kwargs, permission, objs in [
            ("list", {}, "view_algorithm", {ai.algorithm}),
            (
                "job-list",
                {"slug": j.algorithm_image.algorithm.slug},
                "view_job",
                {j},
            ),
        ]:

            def _get_view():
                return get_view_for_user(
                    client=client,
                    viewname=f"algorithms:{view_name}",
                    reverse_kwargs=kwargs,
                    user=u,
                )

            response = _get_view()
            assert response.status_code == 200
            assert set() == {*response.context[-1]["object_list"]}

            assign_perm(permission, u, list(objs))

            response = _get_view()
            assert response.status_code == 200
            assert objs == {*response.context[-1]["object_list"]}

            for obj in objs:
                remove_perm(permission, u, obj)


@pytest.mark.django_db
class TestJobDetailView:
    def test_guarded_content_visibility(self, client):
        j = AlgorithmJobFactory()
        u = UserFactory()
        assign_perm("view_job", u, j)

        for content, permission, permission_object in [
            ("<h2>Viewers</h2>", "change_job", j),
            ("<h2>Logs</h2>", "view_logs", j),
        ]:
            view_kwargs = {
                "client": client,
                "viewname": "algorithms:job-detail",
                "reverse_kwargs": {
                    "slug": j.algorithm_image.algorithm.slug,
                    "pk": j.pk,
                },
                "user": u,
            }
            response = get_view_for_user(**view_kwargs)
            assert response.status_code == 200
            assert content not in response.rendered_content

            assign_perm(permission, u, permission_object)

            response = get_view_for_user(**view_kwargs)
            assert response.status_code == 200
            assert content in response.rendered_content

            remove_perm(permission, u, permission_object)


@pytest.mark.django_db
def test_create_algorithm_for_phase_permission(client):
    phase = PhaseFactory()
    admin, participant, user = UserFactory.create_batch(3)
    phase.challenge.add_admin(admin)
    phase.challenge.add_participant(participant)

    # admin can make a submission only if they are verified
    # and if the phase has been configured properly
    response = get_view_for_user(
        viewname="algorithms:create-for-phase",
        reverse_kwargs={"phase_pk": phase.pk},
        client=client,
        user=admin,
    )
    assert response.status_code == 403
    assert (
        "You need to verify your account before you can do this, you can request this from your profile page."
        in str(response.content)
    )

    VerificationFactory(user=admin, is_verified=True)
    response = get_view_for_user(
        viewname="algorithms:create-for-phase",
        reverse_kwargs={"phase_pk": phase.pk},
        client=client,
        user=admin,
    )
    assert response.status_code == 403
    assert "This phase is not configured for algorithm submission" in str(
        response.content
    )

    phase.archive = ArchiveFactory()
    phase.algorithm_inputs.set([ComponentInterfaceFactory()])
    phase.algorithm_outputs.set([ComponentInterfaceFactory()])
    phase.save()
    response = get_view_for_user(
        viewname="algorithms:create-for-phase",
        reverse_kwargs={"phase_pk": phase.pk},
        client=client,
        user=admin,
    )
    assert response.status_code == 200

    # participant can only create algorithm when verified,
    # when phase is open for submission and
    # when the phase has been configured properly (already the case here)
    response = get_view_for_user(
        viewname="algorithms:create-for-phase",
        reverse_kwargs={"phase_pk": phase.pk},
        client=client,
        user=participant,
    )
    assert response.status_code == 403
    assert (
        "You need to verify your account before you can do this, you can request this from your profile page."
        in str(response.content)
    )

    VerificationFactory(user=participant, is_verified=True)
    response = get_view_for_user(
        viewname="algorithms:create-for-phase",
        reverse_kwargs={"phase_pk": phase.pk},
        client=client,
        user=participant,
    )
    assert response.status_code == 403
    assert "The phase is currently not open for submissions." in str(
        response.content
    )

    phase.submission_limit = 1
    phase.save()

    response = get_view_for_user(
        viewname="algorithms:create-for-phase",
        reverse_kwargs={"phase_pk": phase.pk},
        client=client,
        user=participant,
    )
    assert response.status_code == 200

    # normal user cannot create algorithm for phase
    VerificationFactory(user=user, is_verified=True)
    response = get_view_for_user(
        viewname="algorithms:create-for-phase",
        reverse_kwargs={"phase_pk": phase.pk},
        client=client,
        user=user,
    )
    assert response.status_code == 403
    assert (
        "You need to be either an admin or a participant of the challenge in order to create an algorithm for this phase."
        in str(response.content)
    )


@pytest.mark.django_db
def test_create_algorithm_for_phase_presets(client):
    phase = PhaseFactory()
    admin = UserFactory()
    phase.challenge.add_admin(admin)
    VerificationFactory(user=admin, is_verified=True)

    phase.archive = ArchiveFactory()
    ci1 = ComponentInterfaceFactory()
    ci2 = ComponentInterfaceFactory()
    phase.algorithm_inputs.set([ci1])
    phase.algorithm_outputs.set([ci2])
    phase.hanging_protocol = HangingProtocolFactory()
    phase.workstation_config = WorkstationConfigFactory()
    phase.view_content = {"main": ci1.slug}
    phase.save()

    response = get_view_for_user(
        viewname="algorithms:create-for-phase",
        reverse_kwargs={"phase_pk": phase.pk},
        client=client,
        method=client.post,
        user=admin,
        data={
            "title": "Test algorithm",
            "image_requires_memory_gb": 1,
        },
    )
    assert response.status_code == 302
    assert Algorithm.objects.count() == 1
    algorithm = Algorithm.objects.get()
    assert algorithm.inputs.get() == ci1
    assert algorithm.outputs.get() == ci2
    assert algorithm.hanging_protocol == phase.hanging_protocol
    assert algorithm.workstation_config == phase.workstation_config
    assert algorithm.view_content == phase.view_content
    assert algorithm.contact_email == admin.email
    assert algorithm.logo == phase.challenge.logo
    assert algorithm.display_editors
    assert algorithm.workstation.slug == settings.DEFAULT_WORKSTATION_SLUG
