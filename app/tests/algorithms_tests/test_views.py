import datetime

import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.utils import timezone
from django.utils.text import slugify
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.algorithms.models import (
    AlgorithmImage,
    AlgorithmPermissionRequest,
    Job,
)
from grandchallenge.subdomains.utils import reverse
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
    AlgorithmPermissionRequestFactory,
)
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.factories import StagedFileFactory, UserFactory
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

    algorithm_image = StagedFileFactory(file__filename="test_image.tar.gz")
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
            "chunked_upload": algorithm_image.file_id,
            "requires_memory_gb": 24,
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
        viewname="algorithms:execution-session-create",
        reverse_kwargs={"slug": slugify(ai1.algorithm.slug)},
        client=client,
        user=user,
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_algorithm_permission_request_create(client):
    user = UserFactory()
    alg = AlgorithmFactory(public=False)

    response = get_view_for_user(
        viewname="algorithms:detail",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=user,
        follow=True,
    )

    assert response.status_code == 200
    assert "Request access" in response.rendered_content

    response = get_view_for_user(
        viewname="algorithms:permission-request-create",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=user,
        method=client.post,
        follow=True,
    )

    assert AlgorithmPermissionRequest.objects.count() == 1
    assert response.status_code == 200
    pr = AlgorithmPermissionRequest.objects.get(user=user)
    assert "Request access" in response.rendered_content
    assert pr.status_to_string() in response.rendered_content
    assert pr.status == AlgorithmPermissionRequest.PENDING

    # Calling create again should not create a new permission request object
    response = get_view_for_user(
        viewname="algorithms:permission-request-create",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=user,
        method=client.post,
        follow=True,
    )

    assert AlgorithmPermissionRequest.objects.count() == 1


@pytest.mark.django_db
def test_algorithm_permission_request_update(client):
    user = UserFactory()
    editor = UserFactory()

    alg = AlgorithmFactory(public=True)
    alg.add_editor(editor)

    pr = AlgorithmPermissionRequestFactory(algorithm=alg, user=user)
    assert pr.status == AlgorithmPermissionRequest.PENDING

    response = get_view_for_user(
        viewname="algorithms:permission-request-update",
        reverse_kwargs={"slug": slugify(alg.slug), "pk": pr.pk},
        client=client,
        user=editor,
        method=client.get,
        follow=True,
    )

    assert "review access request for user" in response.rendered_content
    assert "Request access" not in response.rendered_content

    response = get_view_for_user(
        viewname="algorithms:permission-request-update",
        reverse_kwargs={"slug": slugify(alg.slug), "pk": pr.pk},
        client=client,
        user=editor,
        method=client.post,
        follow=True,
        data={"status": "NONEXISTENT"},
    )

    pr.refresh_from_db()
    assert response.status_code == 200
    assert pr.status == AlgorithmPermissionRequest.PENDING

    response = get_view_for_user(
        viewname="algorithms:permission-request-update",
        reverse_kwargs={"slug": slugify(alg.slug), "pk": pr.pk},
        client=client,
        user=editor,
        method=client.post,
        follow=True,
        data={"status": AlgorithmPermissionRequest.REJECTED},
    )

    pr.refresh_from_db()
    assert response.status_code == 200
    assert pr.status == AlgorithmPermissionRequest.REJECTED

    response = get_view_for_user(
        viewname="algorithms:permission-request-update",
        reverse_kwargs={"slug": slugify(alg.slug), "pk": pr.pk},
        client=client,
        user=user,
        method=client.get,
        follow=True,
    )

    assert response.status_code == 403

    # User should not be able to change the status
    response = get_view_for_user(
        viewname="algorithms:permission-request-update",
        reverse_kwargs={"slug": slugify(alg.slug), "pk": pr.pk},
        client=client,
        user=user,
        method=client.post,
        follow=True,
        data={"status": AlgorithmPermissionRequest.ACCEPTED},
    )

    pr.refresh_from_db()
    assert response.status_code == 403
    assert pr.status == AlgorithmPermissionRequest.REJECTED

    response = get_view_for_user(
        viewname="algorithms:permission-request-update",
        reverse_kwargs={"slug": slugify(alg.slug), "pk": pr.pk},
        client=client,
        user=editor,
        method=client.post,
        follow=True,
        data={"status": AlgorithmPermissionRequest.ACCEPTED},
    )

    pr.refresh_from_db()
    assert response.status_code == 200
    assert pr.status == AlgorithmPermissionRequest.ACCEPTED


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
def test_algorithm_detail_flexible_inputs(client):
    editor = UserFactory()

    alg = AlgorithmFactory(use_flexible_inputs=False)
    alg.add_editor(editor)
    AlgorithmImageFactory(algorithm=alg, ready=True)

    flexi_input_url = reverse(
        viewname="algorithms:execution-session-create-new",
        kwargs={"slug": alg.slug},
    )

    response = get_view_for_user(
        viewname="algorithms:detail",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=editor,
        method=client.get,
        follow=True,
        **{"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    assert flexi_input_url not in response.rendered_content

    alg.use_flexible_inputs = True
    alg.save()

    response = get_view_for_user(
        viewname="algorithms:detail",
        reverse_kwargs={"slug": slugify(alg.slug)},
        client=client,
        user=editor,
        method=client.get,
        follow=True,
        **{"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    assert flexi_input_url in response.rendered_content


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
                "execution-session-create",
                {"slug": ai.algorithm.slug},
                "execute_algorithm",
                ai.algorithm,
                None,
            ),
            (
                "execution-session-create-new",
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
class TestComponentInterfaceListView:
    def test_login_required(self, client):
        def _get_view(user):
            return get_view_for_user(
                client=client,
                viewname="algorithms:component-interface-list",
                user=user,
            )

        response = _get_view(user=None)
        assert response.status_code == 302
        assert settings.LOGIN_URL in response.url

        response = _get_view(user=UserFactory())
        assert response.status_code == 200


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
