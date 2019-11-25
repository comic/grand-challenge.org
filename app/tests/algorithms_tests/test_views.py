import pytest
from django.contrib.auth.models import Group
from django.utils.text import slugify

from grandchallenge.algorithms.models import (
    AlgorithmImage,
    AlgorithmPermissionRequest,
)
from grandchallenge.subdomains.utils import reverse
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmPermissionRequestFactory,
)
from tests.factories import StagedFileFactory, UserFactory
from tests.utils import get_view_for_user


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
        AlgorithmFactory(visible_to_public=True),
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
        data={"chunked_upload": algorithm_image.file_id},
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
    alg = AlgorithmFactory(visible_to_public=True)

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

    alg = AlgorithmFactory(visible_to_public=True)
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

    assert "review access request for user" not in response.rendered_content
    assert "Request access" in response.rendered_content

    # User should not be able to change the status to anything other
    # than 'pending'
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
    assert response.status_code == 200
    assert pr.status == AlgorithmPermissionRequest.PENDING

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

    alg = AlgorithmFactory(visible_to_public=True)
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
